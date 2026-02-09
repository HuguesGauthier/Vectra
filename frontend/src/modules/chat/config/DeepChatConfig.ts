/**
 * Deep Chat Configuration
 * Centralized configuration for Deep Chat component
 */

export interface DeepChatConfig {
  // Request configuration
  request?: {
    url?: string;
    method?: string;
    headers?: Record<string, string>;
  };

  // Stream configuration
  stream?: {
    simulation?: boolean;
  };

  // Message styles
  messageStyles?: {
    default?: {
      shared?: {
        bubble?: {
          backgroundColor?: string;
          color?: string;
          padding?: string;
          borderRadius?: string;
          maxWidth?: string;
        };
      };
      user?: {
        bubble?: {
          backgroundColor?: string;
          color?: string;
        };
      };
      ai?: {
        bubble?: {
          backgroundColor?: string;
          color?: string;
        };
      };
    };
  };

  // Input area configuration
  textInput?: {
    placeholder?: {
      text?: string;
    };
    styles?: {
      container?: {
        backgroundColor?: string;
        borderTop?: string;
        padding?: string;
      };
      text?: {
        padding?: string;
        fontSize?: string;
      };
    };
  };

  // Submit button configuration
  submitButtonStyles?: {
    submit?: {
      container?: {
        default?: {
          backgroundColor?: string;
        };
        hover?: {
          backgroundColor?: string;
        };
      };
    };
  };

  // Avatar configuration
  avatars?: {
    default?: {
      styles?: {
        avatar?: {
          width?: string;
          height?: string;
          borderRadius?: string;
        };
      };
    };
    ai?: {
      src?: string;
      styles?: {
        avatar?: {
          backgroundColor?: string;
        };
      };
    };
  };

  // Initial messages
  initialMessages?: Array<{
    role: 'user' | 'ai';
    text: string;
  }>;

  // Other features
  history?: boolean;
  connect?: {
    url?: string;
    method?: string;
    headers?: Record<string, string>;
    stream?: boolean;
  };
}

/**
 * Get Deep Chat configuration based on assistant color
 */
export function getDeepChatConfig(assistantColor?: string): DeepChatConfig {
  return {
    textInput: {
      placeholder: {
        text: 'Type your message...',
      },
      styles: {
        container: {
          backgroundColor: 'var(--q-secondary)',
          borderTop: '1px solid var(--q-third)',
          padding: '16px',
        },
        text: {
          padding: '12px 20px',
          fontSize: '14px',
        },
      },
    },

    messageStyles: {
      default: {
        shared: {
          bubble: {
            backgroundColor: 'var(--q-fourth)',
            color: 'var(--q-text-main)',
            padding: '12px 16px',
            borderRadius: '12px',
            maxWidth: '80%',
          },
        },
        user: {
          bubble: {
            backgroundColor: 'var(--q-primary)',
            color: 'var(--q-text-main)',
          },
        },
        ai: {
          bubble: {
            backgroundColor: 'var(--q-fourth)',
            color: 'var(--q-text-main)',
          },
        },
      },
    },

    submitButtonStyles: {
      submit: {
        container: {
          default: {
            backgroundColor: assistantColor || '#1976d2',
          },
          hover: {
            backgroundColor: assistantColor || '#1565c0',
          },
        },
      },
    },

    avatars: {
      default: {
        styles: {
          avatar: {
            width: '40px',
            height: '40px',
            borderRadius: '50%',
          },
        },
      },
      ai: {
        styles: {
          avatar: {
            backgroundColor: assistantColor || 'var(--q-third)',
          },
        },
      },
    },

    history: true,
  };
}
