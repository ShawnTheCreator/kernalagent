using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading;
using System.Windows.Automation;

namespace Kernel_Agent.Services
{
    /// <summary>
    /// UIElementFinder - Find and interact with UI elements using Windows UI Automation.
    /// 
    /// This enables commands like:
    /// - "Click the Save button"
    /// - "Click File menu then Export"
    /// - "Type in the search box"
    /// </summary>
    public class UIElementFinder
    {
        private const int SEARCH_TIMEOUT_MS = 5000;
        
        /// <summary>
        /// Find a button by its name/text in the active window.
        /// </summary>
        public AutomationElement? FindButton(string buttonName)
        {
            Debug.WriteLine($"[UI-FINDER] Looking for button: '{buttonName}'");
            
            var root = AutomationElement.FocusedElement;
            if (root == null)
            {
                root = AutomationElement.RootElement;
            }
            
            // Walk up to find the window
            var window = GetActiveWindow();
            if (window == null)
            {
                Debug.WriteLine("[UI-FINDER] No active window found");
                return null;
            }
            
            // Search for button with matching name
            var condition = new AndCondition(
                new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Button),
                new PropertyCondition(AutomationElement.NameProperty, buttonName)
            );
            
            var button = window.FindFirst(TreeScope.Descendants, condition);
            
            if (button == null)
            {
                // Try partial match
                Debug.WriteLine($"[UI-FINDER] Exact match failed, trying contains...");
                button = FindElementContaining(window, ControlType.Button, buttonName);
            }
            
            if (button != null)
            {
                Debug.WriteLine($"[UI-FINDER] ✓ Found button: {button.Current.Name}");
            }
            else
            {
                Debug.WriteLine($"[UI-FINDER] ✗ Button not found: {buttonName}");
            }
            
            return button;
        }
        
        /// <summary>
        /// Find a menu item by path (e.g., "File > Save As").
        /// </summary>
        public AutomationElement? FindMenuItem(string menuPath)
        {
            Debug.WriteLine($"[UI-FINDER] Looking for menu: '{menuPath}'");
            
            var parts = menuPath.Split(new[] { ">", "→", "->" }, StringSplitOptions.RemoveEmptyEntries)
                                .Select(p => p.Trim())
                                .ToArray();
            
            if (parts.Length == 0) return null;
            
            var window = GetActiveWindow();
            if (window == null) return null;
            
            AutomationElement? current = null;
            
            foreach (var part in parts)
            {
                if (current == null)
                {
                    // Find top-level menu
                    var menuCondition = new AndCondition(
                        new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.MenuItem),
                        new PropertyCondition(AutomationElement.NameProperty, part)
                    );
                    
                    current = window.FindFirst(TreeScope.Descendants, menuCondition);
                    
                    if (current == null)
                    {
                        // Try menu bar item
                        menuCondition = new AndCondition(
                            new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Menu),
                            new PropertyCondition(AutomationElement.NameProperty, part)
                        );
                        current = window.FindFirst(TreeScope.Descendants, menuCondition);
                    }
                }
                else
                {
                    // Expand current menu first
                    ExpandElement(current);
                    Thread.Sleep(200);
                    
                    // Find child menu item
                    var childCondition = new PropertyCondition(AutomationElement.NameProperty, part);
                    current = current.FindFirst(TreeScope.Descendants, childCondition);
                }
                
                if (current == null)
                {
                    Debug.WriteLine($"[UI-FINDER] ✗ Menu item not found: {part}");
                    return null;
                }
                
                Debug.WriteLine($"[UI-FINDER] ✓ Found menu item: {part}");
            }
            
            return current;
        }
        
        /// <summary>
        /// Find a text box/input field by its label or placeholder.
        /// </summary>
        public AutomationElement? FindTextBox(string labelOrName)
        {
            Debug.WriteLine($"[UI-FINDER] Looking for text box: '{labelOrName}'");
            
            var window = GetActiveWindow();
            if (window == null) return null;
            
            // Try exact name match first
            var condition = new AndCondition(
                new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Edit),
                new PropertyCondition(AutomationElement.NameProperty, labelOrName)
            );
            
            var textBox = window.FindFirst(TreeScope.Descendants, condition);
            
            if (textBox == null)
            {
                // Try finding by automation ID or partial name
                textBox = FindElementContaining(window, ControlType.Edit, labelOrName);
            }
            
            if (textBox != null)
            {
                Debug.WriteLine($"[UI-FINDER] ✓ Found text box: {textBox.Current.Name}");
            }
            
            return textBox;
        }
        
        /// <summary>
        /// Find any element by description (uses multiple strategies).
        /// </summary>
        public AutomationElement? FindElement(string description)
        {
            Debug.WriteLine($"[UI-FINDER] Generic search: '{description}'");
            
            var window = GetActiveWindow();
            if (window == null) return null;
            
            // Try as button first
            var element = FindButton(description);
            if (element != null) return element;
            
            // Try as text box
            element = FindTextBox(description);
            if (element != null) return element;
            
            // Try any element with matching name
            var condition = new PropertyCondition(AutomationElement.NameProperty, description);
            element = window.FindFirst(TreeScope.Descendants, condition);
            
            if (element == null)
            {
                // Try partial match on any element
                element = FindElementContaining(window, null, description);
            }
            
            return element;
        }
        
        /// <summary>
        /// Click on an automation element.
        /// </summary>
        public bool ClickElement(AutomationElement element)
        {
            if (element == null) return false;
            
            Debug.WriteLine($"[UI-FINDER] Clicking element: {element.Current.Name}");
            
            try
            {
                // Method 1: Invoke pattern (for buttons)
                if (element.TryGetCurrentPattern(InvokePattern.Pattern, out object invokePattern))
                {
                    ((InvokePattern)invokePattern).Invoke();
                    Debug.WriteLine("[UI-FINDER] ✓ Clicked via Invoke pattern");
                    return true;
                }
                
                // Method 2: Toggle pattern (for checkboxes)
                if (element.TryGetCurrentPattern(TogglePattern.Pattern, out object togglePattern))
                {
                    ((TogglePattern)togglePattern).Toggle();
                    Debug.WriteLine("[UI-FINDER] ✓ Toggled via Toggle pattern");
                    return true;
                }
                
                // Method 3: Selection pattern
                if (element.TryGetCurrentPattern(SelectionItemPattern.Pattern, out object selectPattern))
                {
                    ((SelectionItemPattern)selectPattern).Select();
                    Debug.WriteLine("[UI-FINDER] ✓ Selected via SelectionItem pattern");
                    return true;
                }
                
                // Method 4: Fall back to clicking at center coordinates
                var rect = element.Current.BoundingRectangle;
                if (!rect.IsEmpty)
                {
                    int x = (int)(rect.X + rect.Width / 2);
                    int y = (int)(rect.Y + rect.Height / 2);
                    
                    Debug.WriteLine($"[UI-FINDER] Clicking at coordinates: ({x}, {y})");
                    
                    // Use WindowsAutomation for the actual click
                    var automation = new WindowsAutomation();
                    automation.Click(x, y);
                    return true;
                }
                
                Debug.WriteLine("[UI-FINDER] ✗ No click method available");
                return false;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[UI-FINDER] ✗ Click failed: {ex.Message}");
                return false;
            }
        }
        
        /// <summary>
        /// Type text into an element (if it's a text field).
        /// </summary>
        public bool TypeInElement(AutomationElement element, string text)
        {
            if (element == null) return false;
            
            Debug.WriteLine($"[UI-FINDER] Typing into: {element.Current.Name}");
            
            try
            {
                // Focus the element
                element.SetFocus();
                Thread.Sleep(100);
                
                // Try ValuePattern first
                if (element.TryGetCurrentPattern(ValuePattern.Pattern, out object valuePattern))
                {
                    ((ValuePattern)valuePattern).SetValue(text);
                    Debug.WriteLine("[UI-FINDER] ✓ Typed via Value pattern");
                    return true;
                }
                
                // Fall back to SendKeys
                System.Windows.Forms.SendKeys.SendWait(text);
                Debug.WriteLine("[UI-FINDER] ✓ Typed via SendKeys");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[UI-FINDER] ✗ Type failed: {ex.Message}");
                return false;
            }
        }
        
        /// <summary>
        /// Get all buttons in the active window (for debugging/discovery).
        /// </summary>
        public List<string> GetAllButtons()
        {
            var buttons = new List<string>();
            var window = GetActiveWindow();
            if (window == null) return buttons;
            
            var condition = new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Button);
            var elements = window.FindAll(TreeScope.Descendants, condition);
            
            foreach (AutomationElement elem in elements)
            {
                var name = elem.Current.Name;
                if (!string.IsNullOrWhiteSpace(name))
                {
                    buttons.Add(name);
                }
            }
            
            Debug.WriteLine($"[UI-FINDER] Found {buttons.Count} buttons: {string.Join(", ", buttons.Take(10))}");
            return buttons;
        }
        
        /// <summary>
        /// Get all interactive elements in the active window.
        /// </summary>
        public List<UIElementInfo> GetAllElements()
        {
            var elements = new List<UIElementInfo>();
            var window = GetActiveWindow();
            if (window == null) return elements;
            
            // Get buttons
            var buttonCondition = new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Button);
            foreach (AutomationElement elem in window.FindAll(TreeScope.Descendants, buttonCondition))
            {
                if (!string.IsNullOrWhiteSpace(elem.Current.Name))
                {
                    elements.Add(new UIElementInfo
                    {
                        Name = elem.Current.Name,
                        Type = "Button",
                        AutomationId = elem.Current.AutomationId,
                        Bounds = elem.Current.BoundingRectangle
                    });
                }
            }
            
            // Get text boxes
            var editCondition = new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Edit);
            foreach (AutomationElement elem in window.FindAll(TreeScope.Descendants, editCondition))
            {
                elements.Add(new UIElementInfo
                {
                    Name = elem.Current.Name,
                    Type = "TextBox",
                    AutomationId = elem.Current.AutomationId,
                    Bounds = elem.Current.BoundingRectangle
                });
            }
            
            // Get menu items
            var menuCondition = new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.MenuItem);
            foreach (AutomationElement elem in window.FindAll(TreeScope.Descendants, menuCondition))
            {
                if (!string.IsNullOrWhiteSpace(elem.Current.Name))
                {
                    elements.Add(new UIElementInfo
                    {
                        Name = elem.Current.Name,
                        Type = "MenuItem",
                        AutomationId = elem.Current.AutomationId,
                        Bounds = elem.Current.BoundingRectangle
                    });
                }
            }
            
            Debug.WriteLine($"[UI-FINDER] Found {elements.Count} total elements");
            return elements;
        }
        
        // ===== HELPER METHODS =====
        
        private AutomationElement? GetActiveWindow()
        {
            try
            {
                var focused = AutomationElement.FocusedElement;
                if (focused == null) return null;
                
                // Walk up to find the window
                var walker = TreeWalker.ControlViewWalker;
                var current = focused;
                
                while (current != null && current != AutomationElement.RootElement)
                {
                    if (current.Current.ControlType == ControlType.Window)
                    {
                        return current;
                    }
                    current = walker.GetParent(current);
                }
                
                // Fallback: get foreground window by handle
                return AutomationElement.RootElement;
            }
            catch
            {
                return null;
            }
        }
        
        private AutomationElement? FindElementContaining(AutomationElement parent, ControlType? type, string nameContains)
        {
            try
            {
                Condition condition;
                if (type != null)
                {
                    condition = new PropertyCondition(AutomationElement.ControlTypeProperty, type);
                }
                else
                {
                    condition = Condition.TrueCondition;
                }
                
                var elements = parent.FindAll(TreeScope.Descendants, condition);
                
                foreach (AutomationElement elem in elements)
                {
                    var name = elem.Current.Name?.ToLower() ?? "";
                    if (name.Contains(nameContains.ToLower()))
                    {
                        return elem;
                    }
                }
            }
            catch { }
            
            return null;
        }
        
        private void ExpandElement(AutomationElement element)
        {
            try
            {
                if (element.TryGetCurrentPattern(ExpandCollapsePattern.Pattern, out object pattern))
                {
                    ((ExpandCollapsePattern)pattern).Expand();
                }
                else
                {
                    // Try clicking to expand
                    ClickElement(element);
                }
            }
            catch { }
        }
    }
    
    /// <summary>
    /// Information about a UI element.
    /// </summary>
    public class UIElementInfo
    {
        public string Name { get; set; } = "";
        public string Type { get; set; } = "";
        public string AutomationId { get; set; } = "";
        public System.Windows.Rect Bounds { get; set; }
    }
}
