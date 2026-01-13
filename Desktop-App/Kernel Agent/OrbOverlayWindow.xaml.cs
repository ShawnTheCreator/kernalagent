using Microsoft.UI.Xaml;
using System;

namespace Kernel_Agent
{
    public partial class OrbOverlayWindow : Microsoft.UI.Xaml.Window
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

        // WinUI 3: Use PointerPressed event instead of OnMouseLeftButtonDown
        protected override void OnPointerPressed(Microsoft.UI.Xaml.Input.PointerRoutedEventArgs e)
        {
            base.OnPointerPressed(e);
            // Restore main window and close orb
            Application.Current.MainWindow.Activate();
            this.Close();
        }
    }
}
