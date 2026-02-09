import 'vue-i18n';

declare module 'vue' {
  export interface ComponentCustomProperties {
    $t: (key: string, ...args: unknown[]) => string;
    $tm: (key: string) => unknown;
  }
}

declare module '@vue/runtime-core' {
  export interface ComponentCustomProperties {
    $t: (key: string, ...args: unknown[]) => string;
    $tm: (key: string) => unknown;
  }
}
