import * as THREE from 'three';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

const canvas = document.getElementById('relay-3d');
const device = document.getElementById('device');

if (canvas && device && window.WebGLRenderingContext) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    premultipliedAlpha: false,
    powerPreference: 'high-performance',
  });
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
    // Match the approved detached rendering: the right rail and its recessed
    // key remain visible, with the top edge falling gently to the right.
    model.rotation.y = THREE.MathUtils.lerp(-0.20, 0, p);
    model.rotation.z = THREE.MathUtils.lerp(0.105, 0, p);
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

  const approvedTexture = new THREE.TextureLoader().load(
    './assets/relay-thin-top-v2.webp?v=1',
    () => {
      // The external texture is mapped onto glTF UVs, whose vertical axis is
      // already converted by the exporter.  Preserve the approved artwork's
      // top-to-bottom orientation.
      approvedTexture.flipY = false;
      // Treat the baked product render as an sRGB photograph.  Without this
      // declaration WebGL interprets it as linear data, washing out the metal
      // grain and making the surface look synthetic.
      approvedTexture.colorSpace = THREE.SRGBColorSpace;
      approvedTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();
      approvedTexture.minFilter = THREE.LinearMipmapLinearFilter;
      approvedTexture.magFilter = THREE.LinearFilter;
      approvedTexture.needsUpdate = true;
      new GLTFLoader().load(
        './assets/models/relay-thin-authoritative.glb?v=6',
        (gltf) => {
          model = gltf.scene;
          const approvedFront = model.getObjectByName('ApprovedFront');
          if (!approvedFront) {
            console.error('Relay 3D model is missing its approved front surface');
            return;
          }
          approvedFront.material = new THREE.MeshBasicMaterial({
            map: approvedTexture,
            transparent: true,
            // Discard the source render's low-alpha drop-shadow fringe.  The
            // former 0.01 threshold preserved it and produced a pale blur
            // around the rotating device.
            alphaTest: 0.5,
            alphaToCoverage: true,
            side: THREE.DoubleSide,
            toneMapped: false,
          });
          scene.add(model);
          window.relay3D.ready = true;
          device.classList.add('webgl-ready');
          render();
        },
        undefined,
        (error) => console.error('Relay 3D model failed to load', error),
      );
    },
    undefined,
    (error) => console.error('Relay approved front texture failed to load', error),
  );
}
