import * as THREE from 'three';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

const canvas = document.getElementById('relay-3d');
const device = document.getElementById('device');

if (canvas && device && window.WebGLRenderingContext) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.58;

  const scene = new THREE.Scene();
  const environmentScene = new RoomEnvironment();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(environmentScene, 0.04).texture;
  environmentScene.dispose();
  pmrem.dispose();

  const camera = new THREE.OrthographicCamera(-0.5, 0.5, 0.5, -0.5, 0.01, 10);
  camera.position.set(0, 0, 3);
  camera.lookAt(0, 0, 0);

  scene.add(new THREE.HemisphereLight(0xfffbf2, 0x5a5146, 0.28));
  const key = new THREE.DirectionalLight(0xfff2dd, 0.68);
  key.position.set(-2.4, -1.7, 3.5);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xdce8ff, 0.24);
  fill.position.set(2.1, 0.1, 2.6);
  scene.add(fill);

  let model = null;
  let currentProgress = 0;

  function ease(value) {
    return value < 0.5 ? 2 * value * value : 1 - Math.pow(-2 * value + 2, 2) / 2;
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    renderer.setSize(width, height, false);
    const aspect = width / height;
    const viewHeight = 1.16;
    camera.top = viewHeight / 2;
    camera.bottom = -viewHeight / 2;
    camera.left = -viewHeight * aspect / 2;
    camera.right = viewHeight * aspect / 2;
    camera.updateProjectionMatrix();
  }

  function render(progress = currentProgress) {
    currentProgress = Math.max(0, Math.min(1, progress));
    if (!model) return;
    const p = ease(currentProgress);

    // One physical object rotates into the phone plane. No view swap occurs.
    /* glTF is Y-up; the Relay face is authored in FreeCAD's XY plane. Keep
       the manufacturing face oriented toward the camera at contact, then
       pitch that same object outward for the detached pose. */
    const mountedFaceX = Math.PI / 2;
    model.rotation.x = THREE.MathUtils.lerp(mountedFaceX - 0.56, mountedFaceX, p);
    model.rotation.y = THREE.MathUtils.lerp(0.20, 0, p);
    model.rotation.z = THREE.MathUtils.lerp(-0.105, 0, p);
    model.position.y = THREE.MathUtils.lerp(-0.012, 0, p);
    model.position.z = THREE.MathUtils.lerp(0.08, 0, p);
    renderer.render(scene, camera);
  }

  window.relay3D = {
    ready: false,
    update(progress) { render(progress); },
  };

  resize();
  const resizeObserver = new ResizeObserver(() => {
    resize();
    render();
  });
  resizeObserver.observe(canvas);

  new GLTFLoader().load(
    './assets/models/relay-thin-authoritative.glb?v=5',
    (gltf) => {
      model = gltf.scene;
      scene.add(model);
      window.relay3D.ready = true;
      device.classList.add('webgl-ready');
      render();
    },
    undefined,
    (error) => console.error('Relay 3D model failed to load', error),
  );
}
