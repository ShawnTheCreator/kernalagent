using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Windowing;
using WinRT.Interop;
using System;

namespace Kernel_Agent
{
    public sealed partial class MainWindow : Window
    {
        public MainWindow()
        {
            try
            {
                this.InitializeComponent();

                // Validate critical UI elements after initialization
                if (AppTitleBar == null)
                {
                    System.Diagnostics.Debug.WriteLine("MainWindow: AppTitleBar is null after InitializeComponent");
                }
                if (MissionRoot == null)
                {
                    System.Diagnostics.Debug.WriteLine("MainWindow: MissionRoot is null after InitializeComponent");
                }
                if (ContentFrame == null)
                {
                    System.Diagnostics.Debug.WriteLine("MainWindow: ContentFrame is null after InitializeComponent");
                }
                if (NavView == null)
                {
                    System.Diagnostics.Debug.WriteLine("MainWindow: NavView is null after InitializeComponent");
                }

                // 1. Extend the content into the title bar for a modern look
                ExtendsContentIntoTitleBar = true;
                SetTitleBar(AppTitleBar);

                // Ensure MissionRoot is visible by default
                if (MissionRoot != null && ContentFrame != null)
                {
                    MissionRoot.Visibility = Visibility.Visible;
                    ContentFrame.Visibility = Visibility.Collapsed;
                }
                else
                {
                    System.Diagnostics.Debug.WriteLine("MainWindow: Cannot set initial visibility - UI elements are null");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"MainWindow Constructor Exception: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"Stack Trace: {ex.StackTrace}");
                throw; // Re-throw to prevent app from running in corrupted state
            }
        }

        private void NavView_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
        {
            try
            {
                if (args == null)
                {
                    System.Diagnostics.Debug.WriteLine("NavView_SelectionChanged: args is null");
                    return;
                }

                if (args.IsSettingsSelected)
                {
                    NavigateToPage(typeof(SettingsPage));
                }
                else
                {
                    var selectedItem = args.SelectedItem as NavigationViewItem;
                    if (selectedItem?.Tag == null) return;

                    string? tag = selectedItem.Tag as string;
                    if (tag == null) return;

                    // Validate critical UI elements before navigation
                    if (ContentFrame == null || MissionRoot == null)
                    {
                        System.Diagnostics.Debug.WriteLine("NavView_SelectionChanged: Critical UI elements are null");
                        return;
                    }

                    switch (tag)
                    {
                        case "mission":
                            ContentFrame.Visibility = Visibility.Collapsed;
                            MissionRoot.Visibility = Visibility.Visible;
                            break;

                        case "forge":
                            NavigateToPage(typeof(ForgePage));
                            break;

                        case "memory":
                            NavigateToPage(typeof(MemoryPage));
                            break;

                        case "history":
                            NavigateToPage(typeof(HistoryPage));
                            break;

                        case "security":
                            NavigateToPage(typeof(SecurityPage));
                            break;

                        case "sandbox": // NEW: Neural Sandbox logic
                            NavigateToPage(typeof(SandboxPage));
                            break;

                        case "marketplace": // NEW: Marketplace logic
                            NavigateToPage(typeof(MarketplacePage));
                            break;

                        default:
                            System.Diagnostics.Debug.WriteLine($"NavView_SelectionChanged: Unknown tag '{tag}'");
                            break;
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"NavView_SelectionChanged Exception: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"Stack Trace: {ex.StackTrace}");
                
                // Attempt to recover by showing mission control
                if (MissionRoot != null && ContentFrame != null)
                {
                    ContentFrame.Visibility = Visibility.Collapsed;
                    MissionRoot.Visibility = Visibility.Visible;
                }
            }
        }

        /// <summary>
        /// World-Class Helper: Handles UI swapping and redundant navigation checks
        /// </summary>
        private void NavigateToPage(Type pageType)
        {
            try
            {
                // Validate inputs
                if (pageType == null)
                {
                    System.Diagnostics.Debug.WriteLine("NavigateToPage: pageType is null");
                    return;
                }

                if (MissionRoot == null || ContentFrame == null)
                {
                    System.Diagnostics.Debug.WriteLine($"NavigateToPage: MissionRoot or ContentFrame is null. MissionRoot: {MissionRoot != null}, ContentFrame: {ContentFrame != null}");
                    return;
                }

                // 1. Swap Visibility
                MissionRoot.Visibility = Visibility.Collapsed;
                ContentFrame.Visibility = Visibility.Visible;

                // 2. Only navigate if we aren't already on that page
                if (ContentFrame.Content?.GetType() != pageType)
                {
                    ContentFrame.Navigate(pageType);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"NavigateToPage Exception: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"Stack Trace: {ex.StackTrace}");
                
                // Attempt to recover by showing mission control
                if (MissionRoot != null)
                {
                    MissionRoot.Visibility = Visibility.Visible;
                }
                if (ContentFrame != null)
                {
                    ContentFrame.Visibility = Visibility.Collapsed;
                }
            }
        }
    }
}