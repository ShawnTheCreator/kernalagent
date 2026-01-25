using System;
using Microsoft.UI.Xaml;
using Kernel_Agent.Services;

namespace Kernel_Agent
{
    /// <summary>
    /// Theme Manager - Handles global theme switching across the entire app
    /// </summary>
    public class ThemeManager
    {
        private static ThemeManager? _instance;
        public static ThemeManager Instance => _instance ??= new ThemeManager();

        public event Action<ElementTheme>? ThemeChanged;

        private ElementTheme _currentTheme = ElementTheme.Default;

        private ThemeManager()
        {
            // Load saved theme on startup
            LoadSavedTheme();
        }

        /// <summary>
        /// Get the current theme
        /// </summary>
        public ElementTheme CurrentTheme => _currentTheme;

        /// <summary>
        /// Apply theme to the entire app
        /// </summary>
        public void ApplyTheme(string themeString)
        {
            var theme = themeString.ToLower() switch
            {
                "dark" => ElementTheme.Dark,
                "light" => ElementTheme.Light,
                _ => ElementTheme.Default
            };

            ApplyTheme(theme);
        }

        /// <summary>
        /// Apply theme to the entire app
        /// </summary>
        public void ApplyTheme(ElementTheme theme)
        {
            _currentTheme = theme;

            try
            {
                // Apply to main window
                var app = Application.Current as App;
                var window = app?.GetMainWindow();
                
                if (window?.Content is FrameworkElement rootElement)
                {
                    rootElement.RequestedTheme = theme;
                    System.Diagnostics.Debug.WriteLine($"[ThemeManager] Applied theme: {theme}");
                }

                // Notify listeners
                ThemeChanged?.Invoke(theme);

                // Save preference
                SaveTheme(theme);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[ThemeManager] Error applying theme: {ex.Message}");
            }
        }

        /// <summary>
        /// Toggle between light and dark themes
        /// </summary>
        public void ToggleTheme()
        {
            var newTheme = _currentTheme == ElementTheme.Dark ? ElementTheme.Light : ElementTheme.Dark;
            ApplyTheme(newTheme);
        }

        /// <summary>
        /// Load saved theme from settings
        /// </summary>
        private void LoadSavedTheme()
        {
            try
            {
                var settings = SettingsService.Instance;
                var themeString = settings.Theme;
                
                var theme = themeString.ToLower() switch
                {
                    "dark" => ElementTheme.Dark,
                    "light" => ElementTheme.Light,
                    _ => ElementTheme.Default
                };

                _currentTheme = theme;
                System.Diagnostics.Debug.WriteLine($"[ThemeManager] Loaded saved theme: {theme}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[ThemeManager] Error loading theme: {ex.Message}");
                _currentTheme = ElementTheme.Dark; // Default to dark
            }
        }

        /// <summary>
        /// Save theme preference
        /// </summary>
        private void SaveTheme(ElementTheme theme)
        {
            try
            {
                var settings = SettingsService.Instance;
                settings.Theme = theme switch
                {
                    ElementTheme.Dark => "dark",
                    ElementTheme.Light => "light",
                    _ => "system"
                };
                _ = settings.SyncToBackendAsync();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[ThemeManager] Error saving theme: {ex.Message}");
            }
        }

        /// <summary>
        /// Get theme name as string
        /// </summary>
        public string GetThemeName()
        {
            return _currentTheme switch
            {
                ElementTheme.Dark => "Dark",
                ElementTheme.Light => "Light",
                _ => "System"
            };
        }
    }
}
