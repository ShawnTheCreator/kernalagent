using Microsoft.EntityFrameworkCore;
using KernalAgentBackend.Models;
using System.Linq;

namespace KernalAgentBackend.Data
{
    public static class DbInitializer
    {
        public static void Initialize(ApplicationDbContext context)
        {
            // Check if we're using an in-memory database
            if (context.Database.IsInMemory())
            {
                // For in-memory database, just ensure it's created
                context.Database.EnsureCreated();
                
                // Check if we already have data
                if (context.Users.Any())
                {
                    return; // DB has been seeded
                }
                
                // Add sample users
                var users = new KernalAgentBackend.Models.User[]
                {
                    new KernalAgentBackend.Models.User 
                    { 
                        Name = "Admin User", 
                        Email = "admin@example.com",
                        PasswordHash = BCrypt.Net.BCrypt.HashPassword("admin123")
                    },
                    new KernalAgentBackend.Models.User 
                    { 
                        Name = "Test User", 
                        Email = "test@example.com",
                        PasswordHash = BCrypt.Net.BCrypt.HashPassword("test123")
                    }
                };
                
                context.Users.AddRange(users);
                context.SaveChanges();
            }
            else
            {
                // For SQL Server or other relational databases
                context.Database.Migrate();
                
                // Check if we already have data
                if (context.Users.Any())
                {
                    return; // DB has been seeded
                }
                
                // Add sample users
                var users = new KernalAgentBackend.Models.User[]
                {
                    new KernalAgentBackend.Models.User 
                    { 
                        Name = "Admin User", 
                        Email = "admin@example.com",
                        PasswordHash = BCrypt.Net.BCrypt.HashPassword("admin123")
                    },
                    new KernalAgentBackend.Models.User 
                    { 
                        Name = "Test User", 
                        Email = "test@example.com",
                        PasswordHash = BCrypt.Net.BCrypt.HashPassword("test123")
                    }
                };
                
                context.Users.AddRange(users);
                context.SaveChanges();
            }
        }
    }
}
