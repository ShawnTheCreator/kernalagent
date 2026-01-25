using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace Kernel_Agent
{
    /// <summary>
    /// World-Class Skill Forge logic for capturing, editing, and saving AI skills.
    /// </summary>
    public sealed partial class ForgePage : Page
    {
        // ObservableCollection allows the UI to update automatically when the list changes
        public ObservableCollection<SkillAction> Actions { get; set; } = new();

        public ForgePage()
        {
            this.InitializeComponent();
            LoadMockData(); // Pre-fill with a few steps for the demo
        }

        private void LoadMockData()
        {
            Actions.Add(new SkillAction { Label = "1. Launch Excel", Delay = 1000, Color = "#4285F4" });
            Actions.Add(new SkillAction { Label = "2. Click 'A1'", Delay = 500, Color = "#8E75FF" });
            Actions.Add(new SkillAction { Label = "3. Type 'Profit'", Delay = 200, Color = "#34A853" });

            RefreshTimeline();
        }

        /// <summary>
        /// Dynamically creates the visual timeline blocks
        /// </summary>
        private void RefreshTimeline()
        {
            TimelineStrip.Children.Clear();
            foreach (var action in Actions)
            {
                var btn = new Button
                {
                    Content = action.Label,
                    Width = 140,
                    Height = 80,
                    CornerRadius = new CornerRadius(8),
                    Background = new SolidColorBrush(Windows.UI.Color.FromArgb(255, 66, 133, 244)), // Simplified
                    Margin = new Thickness(0, 0, 8, 0)
                };
                TimelineStrip.Children.Add(btn);
            }
        }

        /// <summary>
        /// Simulates the skill on the user's desktop before permanent saving
        /// </summary>
        private async void OnSimulateActionClick(object sender, RoutedEventArgs e)
        {
            // World-class apps show "Simulating" status
            var btn = sender as Button;
            if (btn == null) return;
            
            btn.Content = "Simulating...";
            btn.IsEnabled = false;

            await Task.Delay(2000); // Simulate processing time

            btn.Content = "Simulate Action";
            btn.IsEnabled = true;
        }

        /// <summary>
        /// Saves the current skill to Firebase via ApiService
        /// </summary>
        private async void OnSaveSkillClick(object sender, RoutedEventArgs e)
        {
            var btn = sender as Button;
            if (btn == null) return;

            // Validate inputs
            if (string.IsNullOrWhiteSpace(SkillNameTextBox.Text))
            {
                var dialog = new ContentDialog
                {
                    Title = "Validation Error",
                    Content = "Please enter a skill name.",
                    CloseButtonText = "OK",
                    XamlRoot = this.XamlRoot
                };
                await dialog.ShowAsync();
                return;
            }

            if (string.IsNullOrWhiteSpace(IntentSignatureTextBox.Text))
            {
                var dialog = new ContentDialog
                {
                    Title = "Validation Error",
                    Content = "Please enter an intent signature.",
                    CloseButtonText = "OK",
                    XamlRoot = this.XamlRoot
                };
                await dialog.ShowAsync();
                return;
            }

            // Show loading state
            var originalContent = btn.Content;
            btn.Content = "Saving to Firebase...";
            btn.IsEnabled = false;

            try
            {
                var api = Services.ApiService.Instance;
                var skillId = await api.CreateSkillAsync(
                    name: SkillNameTextBox.Text.Trim(),
                    intentSignature: IntentSignatureTextBox.Text.Trim(),
                    description: DescriptionTextBox.Text?.Trim() ?? "Manual skill",
                    confidence: 0.9
                );

                if (!string.IsNullOrEmpty(skillId))
                {
                    // Success!
                    var successDialog = new ContentDialog
                    {
                        Title = "Success",
                        Content = $"Skill '{SkillNameTextBox.Text}' saved successfully!\nSkill ID: {skillId}",
                        CloseButtonText = "OK",
                        XamlRoot = this.XamlRoot
                    };
                    await successDialog.ShowAsync();

                    // Clear form
                    SkillNameTextBox.Text = "";
                    IntentSignatureTextBox.Text = "";
                    DescriptionTextBox.Text = "";
                }
                else
                {
                    // Failed
                    var errorDialog = new ContentDialog
                    {
                        Title = "Save Failed",
                        Content = "Failed to save skill to Firebase. Check debug output for details.",
                        CloseButtonText = "OK",
                        XamlRoot = this.XamlRoot
                    };
                    await errorDialog.ShowAsync();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[FORGE] Save error: {ex.Message}");
                var errorDialog = new ContentDialog
                {
                    Title = "Error",
                    Content = $"An error occurred: {ex.Message}",
                    CloseButtonText = "OK",
                    XamlRoot = this.XamlRoot
                };
                await errorDialog.ShowAsync();
            }
            finally
            {
                btn.Content = originalContent;
                btn.IsEnabled = true;
            }
        }
    }

    /// <summary>
    /// Data model representing a single AI action in a skill
    /// </summary>
    public class SkillAction
    {
        // Provide a safe default so the non-nullable warning is satisfied.
        // Alternatively you could declare 'public required string Label { get; set; }'
        // or use 'string?' and handle nulls, but defaulting to empty string is simplest here.
        public string Label { get; set; } = string.Empty;
        public int Delay { get; set; }
        public string Color { get; set; } = string.Empty;
    }
}