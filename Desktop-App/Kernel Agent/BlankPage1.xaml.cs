using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Shapes;
using Microsoft.UI.Xaml.Media;
using System;

namespace Kernel_Agent
{
    public sealed partial class BlankPage1 : Page
    {
        private Random _rnd = new Random();

        public BlankPage1()
        {
            this.InitializeComponent();
            GenerateNeuralMap();
        }

        private void GenerateNeuralMap()
        {
            // Draw random nodes to simulate a "Brain"
            for (int i = 0; i < 15; i++)
            {
                var x = _rnd.Next(50, 600);
                var y = _rnd.Next(50, 400);

                // Create a "Neuron"
                Ellipse node = new Ellipse
                {
                    Width = 10,
                    Height = 10,
                    Fill = (SolidColorBrush)Application.Current.Resources["GeminiPurpleBrush"]
                };

                Canvas.SetLeft(node, x);
                Canvas.SetTop(node, y);
                NeuralCanvas.Children.Add(node);
            }
        }
    }
}