/**
 * Settings Page
 * User preferences and configuration management
 */

import React, { useState } from 'react';
import {
  Save,
  RotateCcw,
  Check,
  Sun,
  Moon,
  Monitor,
  Globe,
  DollarSign,
  Calendar,
  Settings as SettingsIcon,
  RefreshCw,
  Database,
} from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';
import { usePreferences, Theme, Language, Currency, DateFormat } from '../contexts/PreferencesContext';

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

// Setting Card Component
interface SettingCardProps {
  title: string;
  description: string;
  icon: React.ElementType;
  iconBgColor: string;
  iconColor: string;
  children: React.ReactNode;
}

const SettingCard: React.FC<SettingCardProps> = ({
  title,
  description,
  icon: Icon,
  iconBgColor,
  iconColor,
  children,
}) => (
  <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
    <div className="mb-6 flex items-center gap-4">
      <div className={cn('flex h-12 w-12 items-center justify-center rounded-xl', iconBgColor)}>
        <Icon className={cn('h-6 w-6', iconColor)} />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
    </div>
    {children}
  </div>
);

// Toggle Button Group Component
interface ToggleOption<T> {
  value: T;
  label: string;
  icon?: React.ElementType;
}

interface ToggleGroupProps<T> {
  options: ToggleOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}

function ToggleGroup<T extends string>({ options, value, onChange, label }: ToggleGroupProps<T>) {
  return (
    <div className="mb-4">
      <label className="mb-2 block text-sm font-medium text-gray-700">{label}</label>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const isSelected = value === option.value;
          const Icon = option.icon;
          return (
            <button
              key={option.value}
              onClick={() => onChange(option.value)}
              className={cn(
                'flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all',
                isSelected
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {Icon && <Icon size={16} />}
              {option.label}
              {isSelected && <Check size={16} className="ml-1" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Read-only Setting Display
interface ReadOnlySettingProps {
  label: string;
  value: string;
  description?: string;
}

const ReadOnlySetting: React.FC<ReadOnlySettingProps> = ({ label, value, description }) => (
  <div className="flex items-center justify-between border-b border-gray-100 py-3 last:border-0">
    <div>
      <p className="text-sm font-medium text-gray-700">{label}</p>
      {description && <p className="text-xs text-gray-500">{description}</p>}
    </div>
    <span className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700">{value}</span>
  </div>
);

// Toggle Switch Component
interface ToggleSwitchProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

const ToggleSwitch: React.FC<ToggleSwitchProps> = ({ label, description, checked, onChange }) => (
  <div className="flex items-center justify-between border-b border-gray-100 py-3 last:border-0">
    <div>
      <p className="text-sm font-medium text-gray-700">{label}</p>
      {description && <p className="text-xs text-gray-500">{description}</p>}
    </div>
    <button
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
        checked ? 'bg-blue-600' : 'bg-gray-300'
      )}
    >
      <span
        className={cn(
          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
          checked ? 'translate-x-6' : 'translate-x-1'
        )}
      />
    </button>
  </div>
);

const Settings: React.FC = () => {
  const {
    preferences,
    setTheme,
    setLanguage,
    setCurrency,
    setDateFormat,
    resetToDefaults,
  } = usePreferences();

  const [showSaveNotification, setShowSaveNotification] = useState(false);
  const [integrationSettings, setIntegrationSettings] = useState({
    autoSync: false,
    retryFailed: true,
    syncFrequency: 'daily',
  });

  // Theme options
  const themeOptions: ToggleOption<Theme>[] = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ];

  // Language options
  const languageOptions: ToggleOption<Language>[] = [
    { value: 'en', label: 'English', icon: Globe },
    { value: 'zh', label: '中文', icon: Globe },
  ];

  // Currency options
  const currencyOptions: ToggleOption<Currency>[] = [
    { value: 'USD', label: 'USD ($)', icon: DollarSign },
    { value: 'CNY', label: 'CNY (¥)', icon: DollarSign },
  ];

  // Date format options
  const dateFormatOptions: ToggleOption<DateFormat>[] = [
    { value: 'YYYY-MM-DD', label: '2024-01-15', icon: Calendar },
    { value: 'MM/DD/YYYY', label: '01/15/2024', icon: Calendar },
    { value: 'DD/MM/YYYY', label: '15/01/2024', icon: Calendar },
  ];

  const handleReset = () => {
    resetToDefaults();
    setShowSaveNotification(true);
    setTimeout(() => setShowSaveNotification(false), 3000);
  };

  // Auto-save is enabled - show notification when preferences change
  React.useEffect(() => {
    setShowSaveNotification(true);
    const timer = setTimeout(() => setShowSaveNotification(false), 2000);
    return () => clearTimeout(timer);
  }, [preferences]);

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">System</p>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-sm text-gray-500">Manage your preferences and configuration</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <RotateCcw size={16} />
            Reset to Defaults
          </button>
        </div>
      </div>

      {/* Save Notification */}
      {showSaveNotification && (
        <div className="fixed right-6 top-6 z-50 flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-lg transition-all">
          <Check size={16} />
          Settings saved automatically
        </div>
      )}

      <div className="space-y-6">
        {/* Display Preferences */}
        <SettingCard
          title="Display Preferences"
          description="Customize how the application looks and feels"
          icon={Sun}
          iconBgColor="bg-amber-100"
          iconColor="text-amber-600"
        >
          <ToggleGroup
            label="Theme"
            options={themeOptions}
            value={preferences.theme}
            onChange={setTheme}
          />
          <ToggleGroup
            label="Language"
            options={languageOptions}
            value={preferences.language}
            onChange={setLanguage}
          />
          <ToggleGroup
            label="Currency Display"
            options={currencyOptions}
            value={preferences.currency}
            onChange={setCurrency}
          />
          <ToggleGroup
            label="Date Format"
            options={dateFormatOptions}
            value={preferences.dateFormat}
            onChange={setDateFormat}
          />
        </SettingCard>

        {/* Analysis Parameters (Read-only from config) */}
        <SettingCard
          title="Analysis Parameters"
          description="System configuration for portfolio analysis (read-only)"
          icon={SettingsIcon}
          iconBgColor="bg-blue-100"
          iconColor="text-blue-600"
        >
          <div className="rounded-lg bg-gray-50 p-4">
            <ReadOnlySetting
              label="Risk Preference"
              value="Balanced"
              description="Moderate risk tolerance with diversified approach"
            />
            <ReadOnlySetting
              label="Rebalancing Threshold"
              value="5%"
              description="Trigger rebalancing when drift exceeds this value"
            />
            <ReadOnlySetting
              label="Tax Rate"
              value="25%"
              description="Assumed tax rate for calculations"
            />
            <ReadOnlySetting
              label="Transaction Cost"
              value="0.1%"
              description="Estimated cost per transaction"
            />
            <ReadOnlySetting
              label="Cost Basis Method"
              value="FIFO"
              description="First In, First Out for tax lot tracking"
            />
          </div>
          <p className="mt-4 text-xs text-gray-500">
            * These values are configured in <code className="rounded bg-gray-100 px-1.5 py-0.5">config/settings.yaml</code>
          </p>
        </SettingCard>

        {/* Data Integration */}
        <SettingCard
          title="Data Integration"
          description="Configure data synchronization settings"
          icon={Database}
          iconBgColor="bg-purple-100"
          iconColor="text-purple-600"
        >
          <ToggleSwitch
            label="Auto-Sync"
            description="Automatically sync data from connected sources"
            checked={integrationSettings.autoSync}
            onChange={(checked) => setIntegrationSettings(prev => ({ ...prev, autoSync: checked }))}
          />
          <ToggleSwitch
            label="Retry Failed Syncs"
            description="Automatically retry failed synchronization attempts"
            checked={integrationSettings.retryFailed}
            onChange={(checked) => setIntegrationSettings(prev => ({ ...prev, retryFailed: checked }))}
          />

          <div className="mt-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">Sync Frequency</label>
            <select
              value={integrationSettings.syncFrequency}
              onChange={(e) => setIntegrationSettings(prev => ({ ...prev, syncFrequency: e.target.value }))}
              className="w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            >
              <option value="manual">Manual only</option>
              <option value="hourly">Every hour</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>

          <div className="mt-6 flex gap-3">
            <button className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
              <RefreshCw size={16} />
              Sync Now
            </button>
            <button className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              <Database size={16} />
              Manage Connections
            </button>
          </div>
        </SettingCard>

        {/* About Section */}
        <SettingCard
          title="About"
          description="System information and version"
          icon={Globe}
          iconBgColor="bg-gray-100"
          iconColor="text-gray-600"
        >
          <div className="rounded-lg bg-gray-50 p-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Application</p>
                <p className="text-sm font-semibold text-gray-900">WealthOS Personal Edition</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Version</p>
                <p className="text-sm font-semibold text-gray-900">1.1.0</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Build</p>
                <p className="text-sm font-semibold text-gray-900">2026.01.14</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">License</p>
                <p className="text-sm font-semibold text-gray-900">MIT Open Source</p>
              </div>
            </div>
          </div>
        </SettingCard>
      </div>
    </div>
  );
};

export default Settings;
