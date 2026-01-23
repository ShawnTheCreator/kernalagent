using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media.Imaging;
using System;
using System.Threading.Tasks;

namespace Kernel_Agent
{
    /// <summary>
    /// User Profile Page - displays user info, stats, and account actions
    /// </summary>
    public sealed partial class ProfilePage : Page
    {
        private Services.ApiService _api;

        public ProfilePage()
        {
            this.InitializeComponent();
            _api = Services.ApiService.Instance;
            Loaded += ProfilePage_Loaded;
        }

        private async void ProfilePage_Loaded(object sender, RoutedEventArgs e)
        {
            await LoadUserDataAsync();
        }

        private async Task LoadUserDataAsync()
        {
            try
            {
                System.Diagnostics.Debug.WriteLine("[PROFILE] Loading user data...");

                // Load user info from API/Firebase
                var user = await _api.GetCurrentUserAsync();
                
                if (user != null)
                {
                    System.Diagnostics.Debug.WriteLine($"[PROFILE] User loaded: {user.Name}, Email: {user.Email}");
                    
                    // Update display name
                    DisplayNameText.Text = !string.IsNullOrEmpty(user.Name) ? user.Name : "User";
                    
                    // Update email
                    EmailText.Text = !string.IsNullOrEmpty(user.Email) ? user.Email : "No email";
                    
                    // Update user ID
                    UserIdText.Text = !string.IsNullOrEmpty(user.UserId) 
                        ? $"ID: {user.UserId.Substring(0, Math.Min(12, user.UserId.Length))}..." 
                        : $"ID: {user.Id}";
                    
                    // Set profile picture display name for initials
                    ProfilePictureControl.DisplayName = user.Name ?? "User";
                    
                    // Load profile photo if available
                    if (!string.IsNullOrEmpty(user.PhotoUrl))
                    {
                        try
                        {
                            ProfilePictureControl.ProfilePicture = new BitmapImage(new Uri(user.PhotoUrl));
                            System.Diagnostics.Debug.WriteLine($"[PROFILE] Loaded photo from: {user.PhotoUrl}");
                        }
                        catch (Exception ex)
                        {
                            System.Diagnostics.Debug.WriteLine($"[PROFILE] Failed to load photo: {ex.Message}");
                        }
                    }

                    // Set member since date
                    if (user.CreatedAt.HasValue)
                    {
                        MemberSinceText.Text = user.CreatedAt.Value.ToString("MMM yyyy");
                    }
                    else
                    {
                        MemberSinceText.Text = "Jan 2026";
                    }
                }
                else
                {
                    System.Diagnostics.Debug.WriteLine("[PROFILE] User data is null, showing defaults");
                    DisplayNameText.Text = "User";
                    EmailText.Text = "Not signed in";
                    UserIdText.Text = "ID: N/A";
                    MemberSinceText.Text = "N/A";
                }

                // Load skills count
                try
                {
                    var skills = await _api.GetMySkillsAsync();
                    SkillsCountText.Text = skills.Count.ToString();
                    System.Diagnostics.Debug.WriteLine($"[PROFILE] Skills count: {skills.Count}");
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[PROFILE] Skills load error: {ex.Message}");
                    SkillsCountText.Text = "0";
                }

                // Load sessions count
                try
                {
                    var sessions = await _api.GetMySessionsAsync();
                    SessionsCountText.Text = sessions.Count.ToString();
                    System.Diagnostics.Debug.WriteLine($"[PROFILE] Sessions count: {sessions.Count}");
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[PROFILE] Sessions load error: {ex.Message}");
                    SessionsCountText.Text = "0";
                }

                System.Diagnostics.Debug.WriteLine("[PROFILE] Data loaded successfully");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[PROFILE] Error loading data: {ex.Message}");
                DisplayNameText.Text = "Error";
                EmailText.Text = "Could not load profile";
                UserIdText.Text = "ID: Error";
                SkillsCountText.Text = "0";
                SessionsCountText.Text = "0";
                MemberSinceText.Text = "N/A";
            }
        }

        private void SettingsButton_Click(object sender, RoutedEventArgs e)
        {
            // Navigate to Settings page
            if (Frame != null)
            {
                Frame.Navigate(typeof(SettingsPage));
            }
        }

        private void ApiKeysButton_Click(object sender, RoutedEventArgs e)
        {
            // Navigate to Settings page (Security section)
            // For now, navigate to Settings - in the future could have dedicated page
            if (Frame != null)
            {
                Frame.Navigate(typeof(SettingsPage));
            }
        }

        private async void LogoutButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new ContentDialog
            {
                Title = "Sign Out",
                Content = "Are you sure you want to sign out?",
                PrimaryButtonText = "Sign Out",
                CloseButtonText = "Cancel",
                DefaultButton = ContentDialogButton.Close,
                XamlRoot = this.XamlRoot
            };

            var result = await dialog.ShowAsync();
            if (result == ContentDialogResult.Primary)
            {
                await _api.LogoutAsync();
                
                // Navigate back to trigger login flow
                if (Frame != null && Frame.CanGoBack)
                {
                    Frame.GoBack();
                }
            }
        }
    }
}
