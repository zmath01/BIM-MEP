import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const material = (color) => new THREE.MeshStandardMaterial({ color, roughness: 0.76 });
const pos = (point) => new THREE.Vector3(...point);

export function createViewer(element, model) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  element.append(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#eaf0e9');
  const camera = new THREE.PerspectiveCamera(36, 1, 0.05, 60);
  const orbit = new OrbitControls(camera, renderer.domElement);
  orbit.minDistance = 4;
  orbit.maxDistance = 26;
  orbit.maxPolarAngle = Math.PI / 2 - 0.04;
  scene.add(new THREE.HemisphereLight('#ffffff', '#82968b', 2.0));
  const sun = new THREE.DirectionalLight('#fff5e6', 2.7);
  sun.position.set(0, 7, 4);
  scene.add(sun);
  const fixed = new THREE.Group();
  const dynamic = new THREE.Group();
  scene.add(fixed, dynamic);

  const box = (bounds, color, parent, outline = false) => {
    const min = pos(bounds.min);
    const max = pos(bounds.max);
    const size = max.clone().sub(min);
    const geometry = new THREE.BoxGeometry(size.x, size.y, size.z);
    const object = new THREE.Mesh(geometry, material(color));
    object.position.copy(min.addScaledVector(size, 0.5));
    if (outline) object.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: '#87988e' })));
    parent.add(object);
    return object;
  };
  box({ min: [-0.85, -0.19, -2.95], max: [7.9, -0.03, 2.95] }, '#f5f5ef', fixed);
  const grid = new THREE.GridHelper(8.6, 17, '#97aaa1', '#acbfb5');
  grid.position.set(3.5, 0, 0);
  grid.scale.z = 0.67;
  fixed.add(grid);
  for (const obstacle of model.obstacles) box(obstacle, '#a8a39c', fixed, true);
  for (const [id, terminal] of Object.entries(model.terminals)) {
    const [x, y, z] = model.nodes[id];
    const colors = { OPEN: '#8fbdac', MEET: '#a1b5da', STUDIO: '#d8b082' };
    box({ min: [x - 0.43, y - 0.20, z - 0.31], max: [x + 0.43, y - 0.09, z + 0.31] }, colors[id] ?? '#8fbdac', fixed, true);
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 60;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 256, 60);
    ctx.font = 'bold 25px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#1d3c30';
    ctx.fillText(terminal.name, 128, 30, 242);
    const label = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false }));
    label.scale.set(1.52, 0.36, 1);
    label.position.set(x, y - 0.48, z);
    fixed.add(label);
  }
  const [x, y, z] = model.nodes[model.root];
  box({ min: [x - 0.61, y - 0.28, z - 0.31], max: [x, y + 0.28, z + 0.31] }, '#576e67', fixed, true);
  const render = () => renderer.render(scene, camera);
  const reset = () => {
    camera.position.set(11, 10.4, 12.5);
    orbit.target.set(3.4, 1.25, 0);
    orbit.update();
    render();
  };
  orbit.addEventListener('change', render);
  const resize = () => {
    const { width, height } = element.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    render();
  };
  new ResizeObserver(resize).observe(element);
  reset();
  return {
    reset,
    update(report, selected) {
      for (const mesh of [...dynamic.children]) {
        dynamic.remove(mesh);
        mesh.geometry.dispose();
        mesh.material.dispose();
      }
      for (const segment of report.segments) {
        const a = pos(segment.a);
        const direction = pos(segment.b).sub(a);
        const diameter = segment.diameter + model.duct.insulation * 2;
        const color = segment.id === selected ? '#d48c30' : segment.clashes.length ? '#bc4333' : '#3e947c';
        const cylinder = new THREE.Mesh(new THREE.CylinderGeometry(diameter / 2, diameter / 2, segment.length, 28), material(color));
        cylinder.position.copy(a).addScaledVector(direction, 0.5);
        cylinder.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
        dynamic.add(cylinder);
      }
      render();
    }
  };
}
