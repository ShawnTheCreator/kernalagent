using Microsoft.UI.Xaml;
using System;
using System.Windows;

namespace Kernel_Agent
{
    public partial class OrbOverlayWindow : Window
    {
        public OrbOverlayWindow()
        {
            InitializeComponent();
            Loaded += OrbOverlayWindow_Loaded;
        }

        private void OrbOverlayWindow_Loaded(object sender, RoutedEventArgs e)
        {
            // Position in bottom-right corner
            var desktopWorkingArea = SystemParameters.WorkArea;
            Left = desktopWorkingArea.Right - Width - 30;
            Top = desktopWorkingArea.Bottom - Height - 30;
        }

        protected override void OnMouseLeftButtonDown(System.Windows.Input.MouseButtonEventArgs e)
        {
            base.OnMouseLeftButtonDown(e);
            // Restore main window and hide orb
            Application.Current.MainWindow.Show();
            Hide();
        }
    }
}
