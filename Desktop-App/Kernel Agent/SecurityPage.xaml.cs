using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;
using System.Threading.Tasks;
using Windows.UI.Popups;

namespace Kernel_Agent
{
    /// <summary>
    /// Logic for managing the Agent's safety guardrails and privacy boundaries.
    /// </summary>
    public sealed partial class SecurityPage : Page
    {
        public SecurityPage()
        {
            this.InitializeComponent();
        }

        /// <summary>
        /// Handles the high-stakes "Purge" action. 
        /// In a world-class app, this requires confirmation.
        /// </summary>
        private async void OnPurgeDataClick(object sender, RoutedEventArgs e)
        {
            ContentDialog confirmDialog = new ContentDialog
            {
                Title = "Irreversible Action",
                Content = "This will wipe all learned skills and neural associations. Are you absolutely sure?",
                PrimaryButtonText = "Purge Everything",
                CloseButtonText = "Cancel",
                DefaultButton = ContentDialogButton.Close,
                XamlRoot = this.XamlRoot // Required in WinUI 3
            };

            // Set the style to destructive
            confirmDialog.PrimaryButtonStyle = (Style)Application.Current.Resources["AccentButtonStyle"];

            ContentDialogResult result = await confirmDialog.ShowAsync();

            if (result == ContentDialogResult.Primary)
            {
                // Here you would add the logic to delete local JSON files and DB entries
                await SimulateDataWipe();
            }
        }

        private async Task SimulateDataWipe()
        {
            // Visual feedback for the purge process
            var btn = (Button)FindName("PurgeButton"); // We'll add this name to your XAML
            if (btn != null)
            {
                btn.Content = "WIPING...";
                btn.IsEnabled = false;
                await Task.Delay(2000);
                btn.Content = "DATABASE PURGED";
            }
        }

        /// <summary>
        /// Logic for adding a new app to the restricted list
        /// </summary>
        private void OnAddRestrictedAppClick(object sender, RoutedEventArgs e)
        {
            // This would normally open a process picker. 
            // For the hackathon, we can simulate adding a new entry to the list.
        }
    }
}