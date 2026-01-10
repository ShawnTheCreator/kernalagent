using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.Threading.Tasks;

namespace Kernel_Agent
{
    public sealed partial class SettingsPage : Page
    {
        public SettingsPage()
        {
            this.InitializeComponent();
        }

        /// <summary>
        /// Handles the App Theme selection change.
        /// </summary>
        private void OnThemeSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (sender is ComboBox comboBox && this.Frame != null)
            {
                var selectedTheme = comboBox.SelectedItem as ComboBoxItem;
                if (selectedTheme == null) return;

                // Logic to update the root element theme
                if (Window.Current?.Content is FrameworkElement rootElement)
                {
                    switch (selectedTheme.Content.ToString())
                    {
                        case "Light":
                            rootElement.RequestedTheme = ElementTheme.Light;
                            break;
                        case "Dark":
                            rootElement.RequestedTheme = ElementTheme.Dark;
                            break;
                        default:
                            rootElement.RequestedTheme = ElementTheme.Default;
                            break;
                    }
                }
            }
        }

        /// <summary>
        /// Simulates validating and saving an AI API Key.
        /// </summary>
        private async void OnSaveApiKeyClick(object sender, RoutedEventArgs e)
        {
            // Visual feedback: Show the user the key is being encrypted and saved
            var btn = sender as Button;
            if (btn != null)
            {
                btn.Content = "Validating Key...";
                btn.IsEnabled = false;

                await Task.Delay(1500); // Simulate network check

                btn.Content = "Key Saved Securely";

                // Optional: Re-enable after a delay
                await Task.Delay(2000);
                btn.Content = "Update Key";
                btn.IsEnabled = true;
            }
        }
    }
}