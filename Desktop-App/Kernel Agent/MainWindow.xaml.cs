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
            this.InitializeComponent();

            // 1. Extend the content into the title bar for a modern look
            ExtendsContentIntoTitleBar = true;
            SetTitleBar(AppTitleBar); // AppTitleBar is defined in your XAML

            // Ensure MissionRoot (the MainWindow mission control UI) is visible by default
            MissionRoot.Visibility = Visibility.Visible;
            ContentFrame.Visibility = Visibility.Collapsed;
        }

        /// <summary>
        /// Handles switching between different AI agent screens
        /// </summary>
        private void NavView_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
        {
            if (args.IsSettingsSelected)
            {
                // Optional: ContentFrame.Navigate(typeof(SettingsPage));
            }
            else
            {
                var selectedItem = args.SelectedItem as NavigationViewItem;
                if (selectedItem?.Tag == null) return;

                string? tag = selectedItem.Tag as string;
                if (tag == null) return;

                switch (tag)
                {
                    case "forge":
                        // hide mission UI, show frame and navigate to ForgePage
                        MissionRoot.Visibility = Visibility.Collapsed;
                        if (ContentFrame.Visibility != Visibility.Visible)
                        {
                            ContentFrame.Visibility = Visibility.Visible;
                        }

                        // Avoid redundant navigation
                        if (!(ContentFrame.Content is ForgePage))
                        {
                            ContentFrame.Navigate(typeof(ForgePage));
                        }
                        break;

                    case "mission":
                        // show mission UI, hide frame
                        ContentFrame.Visibility = Visibility.Collapsed;
                        MissionRoot.Visibility = Visibility.Visible;
                        break;

                    case "memory":
                        MissionRoot.Visibility = Visibility.Collapsed;
                        if (ContentFrame.Visibility != Visibility.Visible)
                        {
                            ContentFrame.Visibility = Visibility.Visible;
                        }

                        // Replace with actual MemoryPage when available
                        // if (!(ContentFrame.Content is MemoryPage))
                        // {
                        //     ContentFrame.Navigate(typeof(MemoryPage));
                        // }
                        break;
                }
            }
        }
    }
}