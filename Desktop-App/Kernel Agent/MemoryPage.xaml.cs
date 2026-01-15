using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Shapes;
using Windows.Foundation;
using Windows.UI;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Kernel_Agent.Services;

namespace Kernel_Agent
{
    public sealed partial class MemoryPage : Page
    {
        private static readonly Random _random = new Random();
        private readonly ApiService _api = ApiService.Instance;
        private List<SkillDto> _skills = new();

        public MemoryPage()
        {
            this.InitializeComponent();
        }

        private async void Page_Loaded(object sender, RoutedEventArgs e)
        {
            GenerateNeuralMap();
            await LoadSkillsAsync();
        }

        private async Task LoadSkillsAsync()
        {
            ShowLoading(true);
            
            try
            {
                _skills = await _api.GetMySkillsAsync();
                
                if (_skills.Count > 0)
                {
                    SkillsListView.ItemsSource = _skills;
                    SkillsCountText.Text = $"{_skills.Count} skills learned";
                    CognitiveNodesText.Text = $"SKILLS LOADED: {_skills.Count}";
                    MemoryIntegrityText.Text = "API: CONNECTED";
                    MemoryIntegrityText.Foreground = new SolidColorBrush(Color.FromArgb(255, 52, 168, 83));
                }
                else
                {
                    SkillsCountText.Text = "No skills found";
                    CognitiveNodesText.Text = "SKILLS LOADED: 0";
                    MemoryIntegrityText.Text = "No skills yet - start using commands!";
                    MemoryIntegrityText.Foreground = new SolidColorBrush(Color.FromArgb(255, 251, 188, 4));
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[MEMORY] Load error: {ex.Message}");
                SkillsCountText.Text = "Failed to load";
                MemoryIntegrityText.Text = "API: OFFLINE";
                MemoryIntegrityText.Foreground = new SolidColorBrush(Color.FromArgb(255, 234, 67, 53));
            }
            finally
            {
                ShowLoading(false);
            }
        }

        private void ShowLoading(bool isLoading)
        {
            if (FindName("LoadingProgress") is ProgressRing progress)
            {
                progress.IsActive = isLoading;
                progress.Visibility = isLoading ? Visibility.Visible : Visibility.Collapsed;
            }
            if (FindName("RefreshSkillsButton") is Button btn)
            {
                btn.IsEnabled = !isLoading;
            }
        }

        private void SkillsListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (SkillsListView.SelectedItem is SkillDto skill)
            {
                ShowSkillDetails(skill);
            }
        }

        private void ShowSkillDetails(SkillDto skill)
        {
            // Hide neural canvas, show details panel
            if (FindName("SkillDetailsPanel") is Grid panel)
                panel.Visibility = Visibility.Visible;
            if (FindName("NeuralCanvas") is Canvas canvas)
                canvas.Visibility = Visibility.Collapsed;

            // Populate details
            if (FindName("DetailSkillName") is TextBlock name)
                name.Text = skill.Name;
            if (FindName("DetailSkillIntent") is TextBlock intent)
                intent.Text = skill.IntentSignature;
            if (FindName("DetailConfidence") is TextBlock conf)
                conf.Text = $"{(skill.Confidence * 100):F0}%";
            if (FindName("DetailSuccessCount") is TextBlock count)
                count.Text = skill.SuccessCount.ToString();
            if (FindName("DetailLastUsed") is TextBlock lastUsed)
            {
                if (!string.IsNullOrEmpty(skill.LastUsedAt))
                {
                    if (DateTime.TryParse(skill.LastUsedAt, out var dt))
                        lastUsed.Text = dt.ToString("MMM dd");
                    else
                        lastUsed.Text = skill.LastUsedAt;
                }
                else
                {
                    lastUsed.Text = "Never";
                }
            }
        }

        private async void RefreshSkillsButton_Click(object sender, RoutedEventArgs e)
        {
            await LoadSkillsAsync();
        }

        private void GenerateNeuralMap()
        {
            if (NeuralCanvas == null) return;

            NeuralCanvas.Children.Clear();
            List<Point> nodePoints = new List<Point>();

            var purpleBrush = Application.Current.Resources["GeminiPurpleBrush"] as SolidColorBrush
                              ?? new SolidColorBrush(Color.FromArgb(255, 142, 117, 255));
            var blueBrush = Application.Current.Resources["GoogleBlue"] as SolidColorBrush
                            ?? new SolidColorBrush(Color.FromArgb(255, 66, 133, 244));

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
    }
}