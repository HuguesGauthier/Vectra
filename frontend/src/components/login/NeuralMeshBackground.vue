<template>
  <div ref="container" class="neural-container">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';

const container = ref<HTMLElement | null>(null);
const canvas = ref<HTMLCanvasElement | null>(null);

let ctx: CanvasRenderingContext2D | null = null;
let particles: Particle[] = [];
let width = 0;
let height = 0;
let isLightMode = false;

interface Particle {
  x: number;
  y: number;
  radius: number;
  isGlowing: boolean;
  colorType: 'primary' | 'secondary';
}

const checkTheme = () => {
  isLightMode = document.body.classList.contains('body--light');
  drawCanvas();
};

const handleResize = () => {
  if (!canvas.value || !container.value) return;
  width = container.value.clientWidth;
  height = container.value.clientHeight;
  canvas.value.width = width;
  canvas.value.height = height;
  createParticles();
  drawCanvas();
};

const createParticles = () => {
  particles = [];
  const cx = width / 2;
  const cy = height / 2;

  // Dimensions for the central structure - Tight core, breathable shell
  const coreRadiusX = Math.min(width * 0.2, 200);
  const coreRadiusY = Math.min(height * 0.2, 150);
  const shellRadiusX = Math.min(width * 0.45, 500);
  const shellRadiusY = Math.min(height * 0.45, 350);

  // Higher density to allow for a solid core feel
  const numParticles = 350;

  for (let i = 0; i < numParticles; i++) {
    // Generate normally distributed points (Box-Muller transform)
    let u = 0,
      v = 0;
    while (u === 0) u = Math.random();
    while (v === 0) v = Math.random();
    const z1 = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
    const z2 = Math.sqrt(-2.0 * Math.log(u)) * Math.sin(2.0 * Math.PI * v);

    let x, y;

    // Distribution strategy:
    // 60% in the tight central core
    // 30% in the larger "brain" shell
    // 10% as long branching outliers
    const rand = Math.random();
    if (rand < 0.6) {
      x = cx + z1 * coreRadiusX * 0.4;
      const yOffset = -Math.abs(z1) * coreRadiusY * 0.2;
      y = cy + z2 * coreRadiusY * 0.4 + yOffset;
    } else if (rand < 0.9) {
      x = cx + z1 * shellRadiusX * 0.6;
      y = cy + z2 * shellRadiusY * 0.6;
    } else {
      // Long branches stretching out
      const angle = Math.random() * Math.PI * 2;
      const dist = 0.5 + Math.random() * 0.7; // Far away
      x = cx + Math.cos(angle) * width * dist * 0.6;
      y = cy + Math.sin(angle) * height * dist * 0.6;
    }

    const isGlowing = Math.random() > 0.93;
    const colorType = Math.random() > 0.5 ? 'primary' : 'secondary';

    particles.push({
      x,
      y,
      radius: isGlowing ? Math.random() * 2 + 1.2 : Math.random() * 1.0 + 0.4,
      isGlowing,
      colorType,
    });
  }
};

const hexToRgb = (hex: string): string => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (result && result[1] && result[2] && result[3]) {
    return `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`;
  }
  return '255, 255, 255';
};

const drawCanvas = () => {
  if (!ctx || !container.value) return;
  ctx.clearRect(0, 0, width, height);

  // Fetch the actual overridden CSS variables from app.scss
  const rootStyle = getComputedStyle(document.body);
  const primaryHex = rootStyle.getPropertyValue('--q-primary').trim() || '#323339';
  const secondaryHex = rootStyle.getPropertyValue('--q-secondary').trim() || '#2c2d32';

  const primaryRgb = hexToRgb(primaryHex);
  const secondaryRgb = hexToRgb(secondaryHex);

  // Use the theme's primary/secondary colors for the background fill too
  if (isLightMode) {
    ctx.fillStyle = primaryHex; // Use the main light bg color
    ctx.fillRect(0, 0, width, height);
  } else {
    // Dark mode: secondary (darker) as base
    ctx.fillStyle = secondaryHex;
    ctx.fillRect(0, 0, width, height);
  }

  // Define colors for particles and lines
  const baseDotColor = isLightMode ? 'rgba(100, 110, 140, 0.8)' : 'rgba(210, 230, 255, 0.8)';
  const lineColorBase = isLightMode ? '100, 110, 140' : '160, 190, 255';

  // Longer connections for a more geometric, airy structure
  const connectionDistance = Math.min(width, height) * 0.25;

  for (let i = 0; i < particles.length; i++) {
    const p = particles[i];
    if (!p) continue;

    // Draw particle
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);

    if (p.isGlowing) {
      ctx.shadowBlur = 15;
      ctx.shadowColor = p.colorType === 'primary' ? primaryHex : secondaryHex;
      ctx.fillStyle =
        p.colorType === 'primary' ? `rgba(${primaryRgb}, 1)` : `rgba(${secondaryRgb}, 1)`;
    } else {
      ctx.shadowBlur = 0;
      ctx.fillStyle = baseDotColor;
    }
    ctx.fill();
    ctx.shadowBlur = 0;

    // Ensure connectivity
    const sortedNeighbors = particles
      .map((p2, idx) => {
        if (i === idx) return { idx, dist: Infinity };
        const dist = Math.sqrt((p.x - p2.x) ** 2 + (p.y - p2.y) ** 2);
        return { idx, dist };
      })
      .filter((n) => n.dist < connectionDistance)
      .sort((a, b) => a.dist - b.dist);

    // Connect to up to 8 closest neighbors
    const maxConnections = 8;

    for (let k = 0; k < Math.min(maxConnections, sortedNeighbors.length); k++) {
      const neighbor = sortedNeighbors[k];
      if (!neighbor) continue;

      const p2 = particles[neighbor.idx];
      if (!p2) continue;

      // Draw lines only one way to avoid duplication (if i < j)
      if (i < neighbor.idx) {
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p2.x, p2.y);

        const rawOpacity = 1 - neighbor.dist / connectionDistance;
        // Exponential decay so close lines are solid, far ones fade sharply
        const opacity = Math.pow(rawOpacity, 1.5);

        if (p.isGlowing || p2.isGlowing) {
          const colorRgb =
            (p.isGlowing && p.colorType === 'secondary') ||
            (p2.isGlowing && p2.colorType === 'secondary')
              ? secondaryRgb
              : primaryRgb;
          ctx.strokeStyle = `rgba(${colorRgb}, ${opacity * 0.9})`;
        } else {
          ctx.strokeStyle = `rgba(${lineColorBase}, ${opacity * 0.6})`;
        }

        ctx.lineWidth = 0.8;
        ctx.stroke();

        // TRIANGLE LOGIC: Look for a third neighbor connected to both i and neighbor.idx
        for (let l = k + 1; l < Math.min(maxConnections, sortedNeighbors.length); l++) {
          const neighborK = sortedNeighbors[l];
          if (!neighborK) continue;

          const p3 = particles[neighborK.idx];
          if (!p3) continue;

          // Check if p2 and p3 are close enough to be connected
          const dist23 = Math.sqrt((p2.x - p3.x) ** 2 + (p2.y - p3.y) ** 2);
          if (dist23 < connectionDistance) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.lineTo(p3.x, p3.y);
            ctx.closePath();

            // Choose a color based on participants
            const triRgb =
              p.colorType === 'secondary' ||
              p2.colorType === 'secondary' ||
              p3.colorType === 'secondary'
                ? secondaryRgb
                : primaryRgb;

            // Increased fill opacity for better visibility
            const fillOpacity = Math.pow(rawOpacity, 1.2) * 0.18;
            ctx.fillStyle = `rgba(${triRgb}, ${fillOpacity})`;
            ctx.fill();
          }
        }
      }
    }

    // Failsafe: if the node is isolated, force connect it to the absolute nearest node
    if (sortedNeighbors.length === 0) {
      let nearestDist = Infinity;
      let nearestIdx = -1;
      for (let j = 0; j < particles.length; j++) {
        if (i === j) continue;
        const p2 = particles[j];
        if (!p2) continue;
        const dist = Math.sqrt((p.x - p2.x) ** 2 + (p.y - p2.y) ** 2);
        if (dist < nearestDist) {
          nearestDist = dist;
          nearestIdx = j;
        }
      }

      if (nearestIdx !== -1 && i < nearestIdx) {
        const p2 = particles[nearestIdx];
        if (p2) {
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = `rgba(${lineColorBase}, 0.2)`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
  }
};

const init = () => {
  if (!canvas.value || !container.value) return;
  ctx = canvas.value.getContext('2d');
  checkTheme();
  handleResize();
};

let observer: MutationObserver | null = null;
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (!container.value) return;

  // Use ResizeObserver instead of window resize to guarantee we draw AFTER the container has its dimensions
  resizeObserver = new ResizeObserver(() => {
    handleResize();
  });
  resizeObserver.observe(container.value);

  observer = new MutationObserver(() => {
    checkTheme();
  });
  observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

  // Fallback initial init just in case
  setTimeout(() => init(), 50);
});

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  if (observer) {
    observer.disconnect();
  }
});
</script>

<style scoped>
.neural-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  overflow: hidden;
}

canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
