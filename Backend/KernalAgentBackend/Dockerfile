# Use the official .NET SDK image for building
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Copy csproj file and restore dependencies
COPY ["KernalAgentBackend.csproj", "./"]
RUN dotnet restore "KernalAgentBackend.csproj"

# Copy everything else and build
COPY . .
WORKDIR "/src"
RUN dotnet build "KernalAgentBackend.csproj" -c Release -o /app/build

# Publish the application
FROM build AS publish
RUN dotnet publish "KernalAgentBackend.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Build runtime image
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy published app
COPY --from=publish /app/publish .

# Set environment variables (can be overridden)
ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production

# Expose port
EXPOSE 8080

# Switch to non-root user
USER appuser

# Set entry point
ENTRYPOINT ["dotnet", "KernalAgentBackend.dll"]

