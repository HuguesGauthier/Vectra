export interface Preset {
  name: string;
  bg: string;
  text: string;
  category: 'Popular' | 'Vibrant' | 'Pastel' | 'Dark' | 'Gradient' | 'Professional';
}

export const assistantPresets: Preset[] = [
  // --- POPULAR (High Contrast & Safe) ---
  { name: 'Classic Blue', bg: '#007AFF', text: '#FFFFFF', category: 'Popular' },
  { name: 'Emerald', bg: '#10B981', text: '#FFFFFF', category: 'Popular' },
  { name: 'Crimson', bg: '#DC2626', text: '#FFFFFF', category: 'Popular' },
  { name: 'Midnight', bg: '#1E293B', text: '#FFFFFF', category: 'Popular' },
  { name: 'Tangerine', bg: '#F97316', text: '#FFFFFF', category: 'Popular' },

  // --- VIBRANT (Eye-catching) ---
  { name: 'Hot Pink', bg: '#FF007F', text: '#FFFFFF', category: 'Vibrant' },
  { name: 'Electric Purple', bg: '#9333EA', text: '#FFFFFF', category: 'Vibrant' },
  { name: 'Lime Punch', bg: '#84CC16', text: '#000000', category: 'Vibrant' },
  { name: 'Cyan Blast', bg: '#06B6D4', text: '#000000', category: 'Vibrant' },
  { name: 'Deep Coral', bg: '#FF6B6B', text: '#FFFFFF', category: 'Vibrant' },
  { name: 'Gold Rush', bg: '#EAB308', text: '#000000', category: 'Vibrant' },
  { name: 'Bittersweet', bg: '#FF5A5F', text: '#FFFFFF', category: 'Vibrant' },
  { name: 'Dodger Blue', bg: '#1E90FF', text: '#FFFFFF', category: 'Vibrant' },
  { name: 'Orchid', bg: '#DA70D6', text: '#FFFFFF', category: 'Vibrant' },
  { name: 'Spring Green', bg: '#00FF7F', text: '#000000', category: 'Vibrant' },

  // --- PASTEL (Soft & Friendly) ---
  { name: 'Mint', bg: '#A7F3D0', text: '#064E3B', category: 'Pastel' },
  { name: 'Lavender', bg: '#E9D5FF', text: '#581C87', category: 'Pastel' },
  { name: 'Peach', bg: '#FDE68A', text: '#78350F', category: 'Pastel' },
  { name: 'Sky', bg: '#BAE6FD', text: '#0C4A6E', category: 'Pastel' },
  { name: 'Rose', bg: '#FECDD3', text: '#881337', category: 'Pastel' },
  { name: 'Cream', bg: '#FEF3C7', text: '#78350F', category: 'Pastel' },
  { name: 'Baby Blue', bg: '#BFDBFE', text: '#1E3A8A', category: 'Pastel' },
  { name: 'Lilac', bg: '#DDD6FE', text: '#4C1D95', category: 'Pastel' },
  { name: 'Tea Green', bg: '#D1FAE5', text: '#064E3B', category: 'Pastel' },
  { name: 'Salmon', bg: '#FFDAB9', text: '#8B4513', category: 'Pastel' },

  // --- DARK (Sleek & Modern) ---
  { name: 'Charcoal', bg: '#374151', text: '#FFFFFF', category: 'Dark' },
  { name: 'Slate', bg: '#475569', text: '#F8FAFC', category: 'Dark' },
  { name: 'Obsidian', bg: '#111827', text: '#E5E7EB', category: 'Dark' },
  { name: 'Navy', bg: '#172554', text: '#DBEAFE', category: 'Dark' },
  { name: 'Dark Teal', bg: '#134E4A', text: '#CCFBF1', category: 'Dark' },
  { name: 'Eggplant', bg: '#4C1D95', text: '#EDE9FE', category: 'Dark' },
  { name: 'Maroon', bg: '#7F1D1D', text: '#FEE2E2', category: 'Dark' },
  { name: 'Forest', bg: '#14532D', text: '#DCFCE7', category: 'Dark' },
  { name: 'Cocoa', bg: '#451A03', text: '#FEF3C7', category: 'Dark' },
  { name: 'Graphite', bg: '#27272A', text: '#FFFFFF', category: 'Dark' },

  // --- PROFESSIONAL (Subdued & Trust) ---
  { name: 'Corporate Blue', bg: '#2563EB', text: '#FFFFFF', category: 'Professional' },
  { name: 'Steel', bg: '#64748B', text: '#FFFFFF', category: 'Professional' },
  { name: 'Sage', bg: '#78716C', text: '#FFFFFF', category: 'Professional' },
  { name: 'Ocean', bg: '#0891B2', text: '#FFFFFF', category: 'Professional' },
  { name: 'Royal', bg: '#4F46E5', text: '#FFFFFF', category: 'Professional' },
  { name: 'Burnt Orange', bg: '#EA580C', text: '#FFFFFF', category: 'Professional' },
  { name: 'Berry', bg: '#BE123C', text: '#FFFFFF', category: 'Professional' },
  { name: 'Olive', bg: '#65A30D', text: '#FFFFFF', category: 'Professional' },
  { name: 'Taupe', bg: '#A8A29E', text: '#292524', category: 'Professional' },
  { name: 'Teal', bg: '#0D9488', text: '#FFFFFF', category: 'Professional' },

  // --- EXTRA ---
  { name: 'Violet', bg: '#7C3AED', text: '#FFFFFF', category: 'Vibrant' },
  { name: 'Fuchsia', bg: '#C026D3', text: '#FFFFFF', category: 'Vibrant' },
  { name: 'Indigo', bg: '#4338CA', text: '#FFFFFF', category: 'Professional' },
  { name: 'Cool Gray', bg: '#9CA3AF', text: '#111827', category: 'Professional' },
  { name: 'Warm Gray', bg: '#D6D3D1', text: '#44403C', category: 'Pastel' },
];
