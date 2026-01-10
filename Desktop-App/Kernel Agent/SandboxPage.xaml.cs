using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using System;

namespace Kernel_Agent
{
    // The class name MUST be SandboxPage to match the XAML
    public sealed partial class SandboxPage : Page
    {
        public SandboxPage()
        {
            InitializeComponent();
        }

        private void RunSandboxButton_Click(object sender, RoutedEventArgs e)
        {
            // Simulate running code: echo input to output
            SandboxOutput.Text = $"You entered: {SandboxInput.Text}";
        }

        private void VoiceMicButton_Click(object sender, RoutedEventArgs e)
        {
            SandboxOutput.Text = "Voice input not implemented yet.";
        }


    }
}