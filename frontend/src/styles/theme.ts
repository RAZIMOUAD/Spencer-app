/**
 * Design tokens for the Spencer application.
 * Import from here rather than hard-coding hex values in components.
 */

export const colors = {
  /** Primary navy — headers, sidebar, active states */
  navy: '#1B2A4A',
  /** Accent gold — highlights, buttons, FS value */
  gold: '#C9A84C',

  // Slate grays
  slateLight: '#F1F4F8',
  slate100: '#E2E8F0',
  slate300: '#CBD5E1',
  slate500: '#64748B',
  slate700: '#334155',
  slate900: '#0F172A',

  // Semantic
  success: '#22C55E',
  warning: '#F59E0B',
  error:   '#EF4444',
  info:    '#3B82F6',

  // Backgrounds
  bgPage:  '#F8FAFC',
  bgCard:  '#FFFFFF',
} as const;

export type ColorKey = keyof typeof colors;
