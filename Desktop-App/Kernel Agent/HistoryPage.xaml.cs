using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Kernel_Agent.Services;
using System;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Kernel_Agent
{
    public sealed partial class HistoryPage : Page
    {
        private readonly ApiService _api = ApiService.Instance;
        public ObservableCollection<TimelineEventDto> TimelineEvents { get; } = new();

        public HistoryPage()
        {
            this.InitializeComponent();
            this.Loaded += HistoryPage_Loaded;
        }

        private async void HistoryPage_Loaded(object sender, RoutedEventArgs e)
        {
            await LoadTimelineAsync();
        }

        private async Task LoadTimelineAsync()
        {
            try
            {
                // Show loading state if UI elements exist
                if (FindName("LoadingProgress") is ProgressRing ring) ring.IsActive = true;

                var data = await _api.GetMemoryTimelineAsync(limit: 50);
                
                TimelineEvents.Clear();
                if (data != null && data.Events != null)
                {
                    foreach (var evt in data.Events)
                    {
                        TimelineEvents.Add(evt);
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[HISTORY] Load error: {ex.Message}");
            }
            finally
            {
                if (FindName("LoadingProgress") is ProgressRing ring) ring.IsActive = false;
            }
        }

        private async void RefreshButton_Click(object sender, RoutedEventArgs e)
        {
            await LoadTimelineAsync();
        }
    }
}