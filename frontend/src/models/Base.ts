export class Base {
  id: string;
  created_at: string;
  updated_at: string | undefined;

  constructor(data: Partial<Base> = {}) {
    this.id = data.id || '';
    this.created_at = data.created_at || new Date().toISOString();
    this.updated_at = data.updated_at;
  }
}
