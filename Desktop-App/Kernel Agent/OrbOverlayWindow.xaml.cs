using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Media.Animation;
using Microsoft.UI.Windowing;
using System;
using System.Runtime.InteropServices;
using Windows.Foundation;
using Windows.Graphics;

namespace Kernel_Agent
{
    public partial class OrbOverlayWindow : Microsoft.UI.Xaml.Window
    {
        // Win32 interop for true transparency
        [DllImport("user32.dll")]
        private static extern int GetWindowLong(IntPtr hwnd, int index);
        
        [DllImport("user32.dll")]
        private static extern int SetWindowLong(IntPtr hwnd, int index, int newStyle);
        
        [DllImport("user32.dll")]
        private static extern bool SetLayeredWindowAttributes(IntPtr hwnd, uint crKey, byte bAlpha, uint dwFlags);
        
        [DllImport("dwmapi.dll")]
        private static extern int DwmExtendFrameIntoClientArea(IntPtr hwnd, ref MARGINS margins);
        
        [StructLayout(LayoutKind.Sequential)]
        private struct MARGINS
        {
            public int Left;
            public int Right;
            public int Top;
            public int Bottom;
        }
        
        private const int GWL_EXSTYLE = -20;
        private const int WS_EX_LAYERED = 0x80000;
        private const int WS_EX_TRANSPARENT = 0x20;
        private const int WS_EX_TOOLWINDOW = 0x80;
        private const uint LWA_COLORKEY = 0x1;
        private const uint LWA_ALPHA = 0x2;

        private AppWindow? _appWindow;
        private IntPtr _hwnd;
        private bool _isDragging = false;
        private Point _dragStartPoint;
        private PointInt32 _windowStartPosition;
        private DispatcherTimer? _breathingTimer;
        
        // Events for communication with MainWindow
        public event Action? OnExpandRequested;
        public event Action? OnExitRequested;

        public OrbOverlayWindow()
        {
            InitializeComponent();
            ConfigureWindow();
            StartIdleAnimation();
        }

        private void ConfigureWindow()
        {
            // Get window handle
            _hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
            var windowId = Microsoft.UI.Win32Interop.GetWindowIdFromWindow(_hwnd);
            _appWindow = AppWindow.GetFromWindowId(windowId);

            // Remove window chrome (title bar, borders, buttons)
            if (_appWindow.Presenter is OverlappedPresenter presenter)
            {
                presenter.SetBorderAndTitleBar(false, false);
                presenter.IsAlwaysOnTop = true;
                presenter.IsResizable = false;
            }

            // Set window size
            _appWindow.Resize(new SizeInt32(80, 80));

            MoveToTopCenter();
            
            // Apply Win32 transparency
            MakeWindowTransparent();
        }

        public void MoveToTopCenter(int topMargin = 10)
        {
            if (_appWindow == null) return;

            var displayArea = DisplayArea.Primary;
            if (displayArea == null) return;

            var workArea = displayArea.WorkArea;
            int x = Math.Max(0, (workArea.Width / 2) - 40);
            int y = Math.Max(0, topMargin);
            _appWindow.Move(new PointInt32(x, y));
        }
        
        // Additional Win32 for composition/blur
        [DllImport("user32.dll")]
        private static extern int SetWindowCompositionAttribute(IntPtr hwnd, ref WindowCompositionAttributeData data);
        
        [StructLayout(LayoutKind.Sequential)]
        private struct WindowCompositionAttributeData
        {
            public int Attribute;
            public IntPtr Data;
            public int SizeOfData;
        }
        
        [StructLayout(LayoutKind.Sequential)]
        private struct AccentPolicy
        {
            public int AccentState;
            public int AccentFlags;
            public int GradientColor;
            public int AnimationId;
        }
        
        private const int WCA_ACCENT_POLICY = 19;
        private const int ACCENT_ENABLE_TRANSPARENTGRADIENT = 2;
        private const int ACCENT_ENABLE_BLURBEHIND = 3;
        private const int ACCENT_ENABLE_ACRYLICBLURBEHIND = 4;
        
        private void MakeWindowTransparent()
        {
            try
            {
                // Method 1: Extended style for layered + toolwindow (no click-through)
                int exStyle = GetWindowLong(_hwnd, GWL_EXSTYLE);
                exStyle |= WS_EX_TOOLWINDOW | WS_EX_LAYERED;
                // IMPORTANT: Do NOT add WS_EX_TRANSPARENT so orb remains clickable
                SetWindowLong(_hwnd, GWL_EXSTYLE, exStyle);
                
                // Method 2: DWM extend frame for glass effect
                MARGINS margins = new MARGINS { Left = -1, Right = -1, Top = -1, Bottom = -1 };
                DwmExtendFrameIntoClientArea(_hwnd, ref margins);
                
                // Method 3: Set window composition for full transparency
                var accent = new AccentPolicy
                {
                    AccentState = ACCENT_ENABLE_TRANSPARENTGRADIENT,
                    AccentFlags = 2,
                    GradientColor = 0x00000000 // Fully transparent
                };
                
                int accentSize = Marshal.SizeOf(accent);
                IntPtr accentPtr = Marshal.AllocHGlobal(accentSize);
                Marshal.StructureToPtr(accent, accentPtr, false);
                
                var data = new WindowCompositionAttributeData
                {
                    Attribute = WCA_ACCENT_POLICY,
                    SizeOfData = accentSize,
                    Data = accentPtr
                };
                
                SetWindowCompositionAttribute(_hwnd, ref data);
                Marshal.FreeHGlobal(accentPtr);
                
                // Method 4: Set layered window with 0 color key for black = transparent
                SetLayeredWindowAttributes(_hwnd, 0x00000000, 0, LWA_COLORKEY);
                
                System.Diagnostics.Debug.WriteLine("[ORB] Full transparency applied (clickable)");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[ORB] Transparency error: {ex.Message}");
            }
        }

        #region Drag Functionality

        private void MainOrb_PointerPressed(object sender, PointerRoutedEventArgs e)
        {
            var element = sender as UIElement;
            if (element != null)
            {
                _isDragging = true;
                _dragStartPoint = e.GetCurrentPoint(null).Position;
                _windowStartPosition = _appWindow.Position;
                element.CapturePointer(e.Pointer);
                e.Handled = true;
            }
        }

        private void MainOrb_PointerMoved(object sender, PointerRoutedEventArgs e)
        {
            if (_isDragging)
            {
                var currentPoint = e.GetCurrentPoint(null).Position;
                double deltaX = currentPoint.X - _dragStartPoint.X;
                double deltaY = currentPoint.Y - _dragStartPoint.Y;

                int newX = _windowStartPosition.X + (int)deltaX;
                int newY = _windowStartPosition.Y + (int)deltaY;

                _appWindow.Move(new PointInt32(newX, newY));
                e.Handled = true;
            }
        }

        private void MainOrb_PointerReleased(object sender, PointerRoutedEventArgs e)
        {
            if (_isDragging)
            {
                _isDragging = false;
                var element = sender as UIElement;
                element?.ReleasePointerCapture(e.Pointer);
                
                // Edge snapping
                SnapToNearestEdge();
                e.Handled = true;
            }
        }

        private void SnapToNearestEdge()
        {
            var displayArea = DisplayArea.Primary;
            if (displayArea == null) return;

            var pos = _appWindow.Position;
            var workArea = displayArea.WorkArea;
            int snapMargin = 20;
            int edgeDistance = 10;

            int newX = pos.X;
            int newY = pos.Y;

            // Snap to left edge
            if (pos.X < snapMargin)
                newX = edgeDistance;
            // Snap to right edge
            else if (pos.X > workArea.Width - 80 - snapMargin)
                newX = workArea.Width - 80 - edgeDistance;

            // Snap to top edge
            if (pos.Y < snapMargin)
                newY = edgeDistance;
            // Snap to bottom edge
            else if (pos.Y > workArea.Height - 80 - snapMargin)
                newY = workArea.Height - 80 - edgeDistance;

            if (newX != pos.X || newY != pos.Y)
            {
                _appWindow?.Move(new PointInt32(newX, newY));
            }
        }

        #endregion

        #region Click Handlers

        private void MainOrb_Tapped(object sender, TappedRoutedEventArgs e)
        {
            // Single tap = expand main window
            OnExpandRequested?.Invoke();
        }

        private void ExpandMenuItem_Click(object sender, RoutedEventArgs e)
        {
            OnExpandRequested?.Invoke();
        }

        private void ExitMenuItem_Click(object sender, RoutedEventArgs e)
        {
            OnExitRequested?.Invoke();
        }

        #endregion

        #region Animation States

        public void StartIdleAnimation()
        {
            StopAllAnimations();
            
            // Create breathing glow effect
            _breathingTimer = new DispatcherTimer();
            _breathingTimer.Interval = TimeSpan.FromMilliseconds(50);
            
            double phase = 0;
            _breathingTimer.Tick += (s, e) =>
            {
                phase += 0.05;
                double opacity = 0.3 + 0.3 * Math.Sin(phase); // Oscillate between 0.3 and 0.6
                OuterGlow.Opacity = opacity;
                
                // Subtle scale breathing
                double scale = 1.0 + 0.02 * Math.Sin(phase * 0.5);
                MainOrb.RenderTransform = new ScaleTransform { ScaleX = scale, ScaleY = scale, CenterX = 27, CenterY = 27 };
            };
            _breathingTimer.Start();
            
            // Hide processing ring
            ProcessingRing.IsActive = false;
            ProcessingRing.Visibility = Visibility.Collapsed;
        }

        public void SetProcessing()
        {
            StopAllAnimations();
            
            // Show spinning progress ring
            ProcessingRing.IsActive = true;
            ProcessingRing.Visibility = Visibility.Visible;
            
            // Bright outer glow
            OuterGlow.Opacity = 0.8;
            
            // Faster pulse
            _breathingTimer = new DispatcherTimer();
            _breathingTimer.Interval = TimeSpan.FromMilliseconds(30);
            
            double phase = 0;
            _breathingTimer.Tick += (s, e) =>
            {
                phase += 0.15;
                double scale = 1.0 + 0.05 * Math.Sin(phase);
                MainOrb.RenderTransform = new ScaleTransform { ScaleX = scale, ScaleY = scale, CenterX = 27, CenterY = 27 };
            };
            _breathingTimer.Start();
        }

        public void ShowSuccess()
        {
            // Flash green halo
            SuccessHalo.Opacity = 1;
            
            var timer = new DispatcherTimer();
            timer.Interval = TimeSpan.FromMilliseconds(300);
            timer.Tick += (s, e) =>
            {
                timer.Stop();
                SuccessHalo.Opacity = 0;
                StartIdleAnimation();
            };
            timer.Start();
        }

        /// <summary>
        /// Blue pulsing glow when listening for voice input.
        /// </summary>
        public void SetListening()
        {
            StopAllAnimations();
            
            // Show bright blue listening indicator
            ProcessingRing.IsActive = false;
            ProcessingRing.Visibility = Visibility.Collapsed;
            
            // Intense blue pulse
            _breathingTimer = new DispatcherTimer();
            _breathingTimer.Interval = TimeSpan.FromMilliseconds(40);
            
            double phase = 0;
            _breathingTimer.Tick += (s, e) =>
            {
                phase += 0.12;
                
                // Bright pulsing glow
                double opacity = 0.5 + 0.4 * Math.Sin(phase);
                OuterGlow.Opacity = opacity;
                
                // Slight scale pulse indicating active listening
                double scale = 1.0 + 0.03 * Math.Sin(phase * 2);
                MainOrb.RenderTransform = new ScaleTransform { ScaleX = scale, ScaleY = scale, CenterX = 27, CenterY = 27 };
            };
            _breathingTimer.Start();
            
            System.Diagnostics.Debug.WriteLine("[ORB] Listening mode");
        }

        /// <summary>
        /// Expanding glow when the agent is speaking/responding.
        /// </summary>
        public void SetSpeaking()
        {
            StopAllAnimations();
            
            ProcessingRing.IsActive = false;
            ProcessingRing.Visibility = Visibility.Collapsed;
            
            // Smooth expanding/contracting glow like speech waves
            _breathingTimer = new DispatcherTimer();
            _breathingTimer.Interval = TimeSpan.FromMilliseconds(35);
            
            double phase = 0;
            _breathingTimer.Tick += (s, e) =>
            {
                phase += 0.1;
                
                // Pulsing glow matching speech rhythm
                double opacity = 0.6 + 0.3 * Math.Sin(phase * 1.5);
                OuterGlow.Opacity = opacity;
                
                // More dramatic scale for speaking
                double scale = 1.0 + 0.06 * Math.Sin(phase);
                MainOrb.RenderTransform = new ScaleTransform { ScaleX = scale, ScaleY = scale, CenterX = 27, CenterY = 27 };
            };
            _breathingTimer.Start();
            
            System.Diagnostics.Debug.WriteLine("[ORB] Speaking mode");
        }

        private void StopAllAnimations()
        {
            _breathingTimer?.Stop();
            _breathingTimer = null;
        }

        #endregion

        // Clean up when window closes
        private void Window_Closed(object sender, WindowEventArgs args)
        {
            StopAllAnimations();
        }
    }
}
