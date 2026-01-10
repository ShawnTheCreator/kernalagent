using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;

namespace Kernel_Agent
{
    // The class name MUST be MarketplacePage to match the XAML
    public class MarketplaceApp
    {
        public string Name { get; set; }
        public string Description { get; set; }
    }

    public sealed partial class MarketplacePage : Page
    {
        public MarketplacePage()
        {
            InitializeComponent();
            var featuredApps = new[]
            {
                new MarketplaceApp { Name = "Skill: Data Analyzer", Description = "Analyze datasets with AI." },
                new MarketplaceApp { Name = "Extension: Voice Control", Description = "Control the agent with your voice." },
                new MarketplaceApp { Name = "Tool: Web Scraper", Description = "Extract information from websites." }
            };
            var itemsControl = this.FindName("MarketplaceFeaturedItemsControl") as ItemsControl;
            if (itemsControl != null)
                itemsControl.ItemsSource = featuredApps;
        }
    }
}