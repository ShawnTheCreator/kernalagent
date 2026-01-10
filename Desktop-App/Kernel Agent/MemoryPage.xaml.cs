using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Shapes;
using Windows.Foundation;
using Windows.UI; // For Color
using System;
using System.Collections.Generic;

namespace Kernel_Agent
{
    public sealed partial class MemoryPage : Page
    {
        private static readonly Random _random = new Random();

        public MemoryPage()
        {
            this.InitializeComponent();
            this.Loaded += (s, e) => GenerateNeuralMap();
        }

        // Standard implementation for internal calls
        private void GenerateNeuralMap()
        {
            if (NeuralCanvas == null) return;

            NeuralCanvas.Children.Clear();
            List<Point> nodePoints = new List<Point>();

            // Retrieval of brushes with hardcoded fallbacks if Resources are missing
            var purpleBrush = Application.Current.Resources["GeminiPurpleBrush"] as SolidColorBrush
                              ?? new SolidColorBrush(Color.FromArgb(255, 142, 117, 255));
            var blueBrush = Application.Current.Resources["GoogleBlue"] as SolidColorBrush
                            ?? new SolidColorBrush(Color.FromArgb(255, 66, 133, 244));

            // Compute safe bounds based on current window size
            int maxX = (int)Math.Max(NeuralCanvas.ActualWidth - 40, 100);
            int maxY = (int)Math.Max(NeuralCanvas.ActualHeight - 40, 100);

            for (int i = 0; i < 22; i++)
            {
                double x = _random.Next(40, maxX);
                double y = _random.Next(40, maxY);
                nodePoints.Add(new Point(x, y));

                Ellipse neuron = new Ellipse
                {
                    Width = 8,
                    Height = 8,
                    Fill = purpleBrush,
                    Opacity = 0.8
                };

                Canvas.SetLeft(neuron, x - 4);
                Canvas.SetTop(neuron, y - 4);
                NeuralCanvas.Children.Add(neuron);
            }

            for (int i = 0; i < nodePoints.Count; i++)
            {
                for (int connections = 0; connections < 2; connections++)
                {
                    int targetIndex = _random.Next(0, nodePoints.Count);
                    if (targetIndex == i) continue;

                    Line synapse = new Line
                    {
                        X1 = nodePoints[i].X,
                        Y1 = nodePoints[i].Y,
                        X2 = nodePoints[targetIndex].X,
                        Y2 = nodePoints[targetIndex].Y,
                        Stroke = blueBrush,
                        StrokeThickness = 0.5,
                        Opacity = 0.15
                    };
                    NeuralCanvas.Children.Insert(0, synapse);
                }
            }
        }

        // This handles the button click from XAML
        private void OnOptimizeWeightsClick(object sender, RoutedEventArgs e)
        {
            GenerateNeuralMap();
        }
    }
}