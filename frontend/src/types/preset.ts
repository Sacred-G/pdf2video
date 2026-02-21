export interface PresetSettings {
  voice: string;
  resolution: string;
  fps: number;
  generate_backgrounds: boolean;
}

export interface Preset {
  id: string;
  name: string;
  description: string;
  settings: PresetSettings;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface PresetListResponse {
  items: Preset[];
  total: number;
}
