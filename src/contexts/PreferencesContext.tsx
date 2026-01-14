/**
 * Preferences Context
 *
 * Manages user preferences stored in localStorage.
 * Provides theme, language, currency, and date format settings.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Types
export type Theme = 'light' | 'dark' | 'system';
export type Language = 'en' | 'zh';
export type Currency = 'USD' | 'CNY';
export type DateFormat = 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD';

export interface UserPreferences {
  theme: Theme;
  language: Language;
  currency: Currency;
  dateFormat: DateFormat;
}

interface PreferencesContextType {
  preferences: UserPreferences;
  setTheme: (theme: Theme) => void;
  setLanguage: (language: Language) => void;
  setCurrency: (currency: Currency) => void;
  setDateFormat: (dateFormat: DateFormat) => void;
  resetToDefaults: () => void;
  isDarkMode: boolean;
}

// Default preferences
const DEFAULT_PREFERENCES: UserPreferences = {
  theme: 'light',
  language: 'en',
  currency: 'USD',
  dateFormat: 'YYYY-MM-DD',
};

// localStorage key
const STORAGE_KEY = 'wealthos_preferences';

// Context
const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

// Helper to get system theme preference
function getSystemTheme(): 'light' | 'dark' {
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'light';
}

// Helper to load preferences from localStorage
function loadPreferences(): UserPreferences {
  if (typeof window === 'undefined') return DEFAULT_PREFERENCES;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_PREFERENCES, ...parsed };
    }
  } catch (e) {
    console.warn('Failed to load preferences from localStorage:', e);
  }
  return DEFAULT_PREFERENCES;
}

// Helper to save preferences to localStorage
function savePreferences(preferences: UserPreferences): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch (e) {
    console.warn('Failed to save preferences to localStorage:', e);
  }
}

// Provider component
export const PreferencesProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [preferences, setPreferences] = useState<UserPreferences>(loadPreferences);

  // Compute effective dark mode
  const isDarkMode = preferences.theme === 'dark' ||
    (preferences.theme === 'system' && getSystemTheme() === 'dark');

  // Apply theme class to document
  useEffect(() => {
    const root = document.documentElement;
    if (isDarkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [isDarkMode]);

  // Listen for system theme changes when using 'system' theme
  useEffect(() => {
    if (preferences.theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      // Force re-render to update isDarkMode
      setPreferences(prev => ({ ...prev }));
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [preferences.theme]);

  // Persist preferences whenever they change
  useEffect(() => {
    savePreferences(preferences);
  }, [preferences]);

  const setTheme = (theme: Theme) => {
    setPreferences(prev => ({ ...prev, theme }));
  };

  const setLanguage = (language: Language) => {
    setPreferences(prev => ({ ...prev, language }));
    // Note: Actual i18n integration would be done here
    // For now, we just store the preference
  };

  const setCurrency = (currency: Currency) => {
    setPreferences(prev => ({ ...prev, currency }));
  };

  const setDateFormat = (dateFormat: DateFormat) => {
    setPreferences(prev => ({ ...prev, dateFormat }));
  };

  const resetToDefaults = () => {
    setPreferences(DEFAULT_PREFERENCES);
  };

  return (
    <PreferencesContext.Provider
      value={{
        preferences,
        setTheme,
        setLanguage,
        setCurrency,
        setDateFormat,
        resetToDefaults,
        isDarkMode,
      }}
    >
      {children}
    </PreferencesContext.Provider>
  );
};

// Hook to use preferences
export function usePreferences(): PreferencesContextType {
  const context = useContext(PreferencesContext);
  if (context === undefined) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return context;
}
