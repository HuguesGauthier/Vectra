<template>
  <q-card flat class="bg-transparent relative-position flex flex-center" style="overflow: visible">
    <div ref="canvasContainer" id="canvas-container" style="width: 100%; height: 100%"></div>
  </q-card>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue';
import * as THREE from 'three';

const props = defineProps({
  colorLeft: { type: String, default: '#2A4B7C' },
  colorRight: { type: String, default: '#E08E45' },
  colorMid: { type: String, default: '#7D6868' },
  disableAnimation: { type: Boolean, default: false },
  small: { type: Boolean, default: false },
});

const canvasContainer = ref<HTMLElement | null>(null);
let renderer: THREE.WebGLRenderer | null = null;
let animationId: number | null = null;
let resizeObserver: ResizeObserver | null = null;
let onMouseMove: ((event: MouseEvent) => void) | null = null;

onMounted(() => {
  if (!canvasContainer.value) return;

  const container = canvasContainer.value;
  const scene = new THREE.Scene();

  const camera = new THREE.PerspectiveCamera(
    50,
    container.clientWidth / container.clientHeight,
    0.1,
    1000,
  );
  camera.position.z = 30; // Move back slightly to fit sphere completely

  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  container.appendChild(renderer.domElement);

  // --- Configuration des couleurs ---
  // Use props or defaults
  const color1Hex = new THREE.Color(props.colorLeft);
  const color2Hex = new THREE.Color(props.colorRight);
  const whiteColor = new THREE.Color(0xb4cde9);

  // --- PARTIE 1 : La Network Sphere (Externe) ---
  const geometry = new THREE.IcosahedronGeometry(10, props.small ? 1 : 2);

  const applyGradient = (geo: THREE.BufferGeometry) => {
    const positions = geo.attributes.position;
    if (!positions) return;
    const count = positions.count;
    const colors = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const y = positions.getY(i);
      const alpha = (y + 10) / 40;
      const color = new THREE.Color().lerpColors(color2Hex, color1Hex, alpha);
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  };

  const wireframeGeo = new THREE.WireframeGeometry(geometry);
  applyGradient(wireframeGeo);

  const lineMaterial = new THREE.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.4,
  });
  const lines = new THREE.LineSegments(wireframeGeo, lineMaterial);

  const sphereGeo = new THREE.SphereGeometry(
    props.small ? 0.25 : 0.15,
    props.small ? 6 : 16,
    props.small ? 6 : 16,
  );
  const sphereMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const positionAttribute = geometry.attributes.position as THREE.BufferAttribute;

  const vertexCount = positionAttribute.count;
  const spheres = new THREE.InstancedMesh(sphereGeo, sphereMat, vertexCount);
  const dummy = new THREE.Object3D();
  const tempColor = new THREE.Color();

  const getBaseColor = (y: number, target: THREE.Color) => {
    const alpha = (y + 10) / 20;
    target.lerpColors(color2Hex, color1Hex, alpha);
    return target;
  };

  for (let i = 0; i < vertexCount; i++) {
    const x = positionAttribute.getX(i);
    const y = positionAttribute.getY(i);
    const z = positionAttribute.getZ(i);
    dummy.position.set(x, y, z);
    dummy.updateMatrix();
    spheres.setMatrixAt(i, dummy.matrix);

    getBaseColor(y, tempColor);
    spheres.setColorAt(i, tempColor);
  }
  spheres.instanceMatrix.needsUpdate = true;
  if (spheres.instanceColor) spheres.instanceColor.needsUpdate = true;

  // --- PARTIE 2 : La sphère interne Shader ---
  const innerRadius = 8.2;
  const innerGeo = new THREE.IcosahedronGeometry(innerRadius, props.small ? 3 : 20);

  const vertexShader = `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vViewPosition = -mvPosition.xyz;
      gl_Position = projectionMatrix * mvPosition;
    }
  `;

  const fragmentShader = `
    uniform vec3 colorTop;
    uniform vec3 colorBottom;
    uniform float time;
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    // Simplex Noise (identique à avant)
    vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
    vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
    float snoise(vec3 v) {
      const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
      const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
      vec3 i  = floor(v + dot(v, C.yyy) );
      vec3 x0 = v - i + dot(i, C.xxx) ;
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min( g.xyz, l.zxy );
      vec3 i2 = max( g.xyz, l.zxy );
      vec3 x1 = x0 - i1 + C.xxx;
      vec3 x2 = x0 - i2 + C.yyy;
      vec3 x3 = x0 - D.yyy;
      i = mod289(i); 
      vec4 p = permute( permute( permute( 
                i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
              + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) 
              + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
      float n_ = 0.142857142857;
      vec3  ns = n_ * D.wyz - D.xzx;
      vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_ );
      vec4 x = x_ *ns.x + ns.yyyy;
      vec4 y = y_ *ns.x + ns.yyyy;
      vec4 h = 1.0 - abs(x) - abs(y);
      vec4 b0 = vec4( x.xy, y.xy );
      vec4 b1 = vec4( x.zw, y.zw );
      vec4 s0 = floor(b0)*2.0 + 1.0;
      vec4 s1 = floor(b1)*2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));
      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
      vec3 p0 = vec3(a0.xy,h.x);
      vec3 p1 = vec3(a0.zw,h.y);
      vec3 p2 = vec3(a1.xy,h.z);
      vec3 p3 = vec3(a1.zw,h.w);
      vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
      p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
    }

    void main() {
      vec3 normal = normalize(vNormal);
      vec3 viewDir = normalize(vViewPosition);
      float fresnel = dot(viewDir, normal);
      fresnel = clamp(1.2 - fresnel, 0.0, 1.0);
      float rim = pow(fresnel, 2.5); 
      vec3 baseGradient = mix(colorBottom, colorTop, vUv.y);
      float noiseVal = snoise(vNormal * 2.5 + (time * 0.1)); 
      vec3 spotColor = baseGradient * (0.4 + 0.6 * smoothstep(-0.5, 0.5, noiseVal));
      vec3 glowColor = vec3(0.6, 0.8, 1.0);
      vec3 finalColor = mix(spotColor, glowColor, rim * 0.8);
      float alpha = 0.8 + (rim * 0.2);
      gl_FragColor = vec4(finalColor, alpha);
    }
  `;

  const customMaterial = new THREE.ShaderMaterial({
    uniforms: {
      colorTop: { value: color1Hex },
      colorBottom: { value: color2Hex },
      time: { value: 0 },
    },
    vertexShader: vertexShader,
    fragmentShader: fragmentShader,
    transparent: true,
    side: THREE.FrontSide,
  });

  const innerSphereMesh = new THREE.Mesh(innerGeo, customMaterial);

  const sphereGroup = new THREE.Group();
  sphereGroup.add(lines);
  sphereGroup.add(spheres);
  sphereGroup.add(innerSphereMesh);
  scene.add(sphereGroup);

  // --- Animation State ---
  let mouseX = 0;
  let mouseY = 0;
  let targetX = 0;
  let targetY = 0;
  const windowHalfX = window.innerWidth / 2;
  const windowHalfY = window.innerHeight / 2;

  // --- LOGIQUE FADE IN / FADE OUT (PULSE) ---
  let activePulseIndex: number | null = null;
  let pulseStartTime = 0;
  const pulseDuration = 1;
  let nextPulseTime = 0;

  const resetPoint = (index: number) => {
    const x = positionAttribute.getX(index);
    const y = positionAttribute.getY(index);
    const z = positionAttribute.getZ(index);

    dummy.position.set(x, y, z);
    dummy.scale.set(1, 1, 1);
    dummy.updateMatrix();
    spheres.setMatrixAt(index, dummy.matrix);

    getBaseColor(y, tempColor);
    spheres.setColorAt(index, tempColor);

    spheres.instanceMatrix.needsUpdate = true;
    if (spheres.instanceColor) spheres.instanceColor.needsUpdate = true;
  };

  onMouseMove = (event: MouseEvent) => {
    mouseX = event.clientX - windowHalfX;
    mouseY = event.clientY - windowHalfY;
  };
  document.addEventListener('mousemove', onMouseMove);

  const clock = new THREE.Clock();

  function animate() {
    animationId = requestAnimationFrame(animate);
    const elapsedTime = clock.getElapsedTime();

    if (customMaterial.uniforms.time) {
      customMaterial.uniforms.time.value = elapsedTime;
    }

    if (activePulseIndex === null && elapsedTime > nextPulseTime) {
      activePulseIndex = Math.floor(Math.random() * vertexCount);
      pulseStartTime = elapsedTime;
    }

    if (activePulseIndex !== null) {
      const progress = (elapsedTime - pulseStartTime) / pulseDuration;

      if (progress >= 1) {
        resetPoint(activePulseIndex);
        activePulseIndex = null;
        nextPulseTime = elapsedTime + Math.random() * 0.5 + 0.2;
      } else {
        const intensity = Math.sin(progress * Math.PI);
        const scale = 0.1 + intensity * 1.5;
        const x = positionAttribute.getX(activePulseIndex);
        const y = positionAttribute.getY(activePulseIndex);
        const z = positionAttribute.getZ(activePulseIndex);

        dummy.position.set(x, y, z);
        dummy.scale.set(scale, scale, scale);
        dummy.updateMatrix();
        spheres.setMatrixAt(activePulseIndex, dummy.matrix);

        getBaseColor(y, tempColor);
        tempColor.lerp(whiteColor, intensity);
        spheres.setColorAt(activePulseIndex, tempColor);

        spheres.instanceMatrix.needsUpdate = true;
        if (spheres.instanceColor) spheres.instanceColor.needsUpdate = true;
      }
    }

    sphereGroup.rotation.y += 0.002;
    sphereGroup.rotation.x += 0.001;

    if (!props.disableAnimation) {
      const scale = 1 + Math.sin(elapsedTime * 0.25) * 0.15;
      sphereGroup.scale.set(scale, scale, scale);
      targetX = mouseX * 0.001;
      targetY = mouseY * 0.001;
      sphereGroup.rotation.y += 0.05 * (targetX - sphereGroup.rotation.y);
      sphereGroup.rotation.x += 0.05 * (targetY - sphereGroup.rotation.x);
    } else {
      sphereGroup.scale.set(1, 1, 1);
    }

    if (renderer) renderer.render(scene, camera);
  }

  animate();

  const onResize = () => {
    if (!container || !renderer || !camera) return;
    const width = container.clientWidth;
    const height = container.clientHeight;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };

  resizeObserver = new ResizeObserver(() => onResize());
  resizeObserver.observe(container);
  onResize();
});

onBeforeUnmount(() => {
  if (onMouseMove) document.removeEventListener('mousemove', onMouseMove);
  if (resizeObserver) resizeObserver.disconnect();
  if (animationId) cancelAnimationFrame(animationId);
  if (renderer) {
    renderer.dispose();
    if (
      canvasContainer.value &&
      renderer.domElement &&
      canvasContainer.value.contains(renderer.domElement)
    ) {
      canvasContainer.value.removeChild(renderer.domElement);
    }
  }
});
</script>
