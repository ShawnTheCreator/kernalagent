
<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/ShawnTheCreator/kernalagent">
    <img width="698" height="376" alt="image" src="https://github.com/user-attachments/assets/55e7cd94-7579-497f-9fb0-d2ff82dd7cd2" />

  </a>

  <h3 align="center">Kernel Agent</h3>

  <p align="center">
    An advanced, autonomous AI desktop assistant designed to integrate seamlessly with your workflow.
    <br />
    <a href="https://github.com/ShawnTheCreator/kernalagent"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/ShawnTheCreator/kernalagent">View Demo</a>
    &middot;
    <a href="https://github.com/ShawnTheCreator/kernalagent/issues">Report Bug</a>
    &middot;
    <a href="https://github.com/ShawnTheCreator/kernalagent/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#architecture">Architecture</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

**Kernel Agent** is a next-generation desktop automation platform that combines a native Windows application with powerful AI microservices. It is designed to act as a true digital companion, capable of understanding voice commands, seeing your screen, and executing complex tasks across your operating system.

Key features include:
*   **Holographic Desktop Overlay**: A sleek, non-intrusive UI built with WinUI 3 that provides instant access to AI capabilities.
*   **Multi-Modal AI**: Integrates Google Gemini, Computer Vision (OpenCV/EasyOCR), and Voice Recognition (Vosk/Google Speech) for a seamless interaction model.
*   **Autonomous Agents**: Includes specialized agents like "Janitor" for system maintenance and "Sentinel" for security monitoring.
*   **Extensible Architecture**: Built on a microservice architecture allowing for easy addition of new capabilities and agents.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

The project is built using a robust stack of modern technologies:

*   **Desktop Application:**
    *   [![DotNet][DotNet-badge]][DotNet-url] **.NET 9.0** & **WinUI 3**
    *   **C#** for core application logic and OS integration
*   **AI Microservice:**
    *   [![Python][Python-badge]][Python-url] **FastAPI**
    *   **PyTorch** & **OpenCV** for ML and Vision
    *   **Google Gemini** for reasoning and generation
*   **Frontend / Web Dashboard:**
    *   [![Next][Next.js]][Next-url]
    *   [![React][React.js]][React-url]
    *   [![TailwindCSS][TailwindCSS-badge]][TailwindCSS-url]
    *   **Three.js** & **React Three Fiber** for 3D visualizations

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running, follow these steps.

### Prerequisites

Ensure you have the following installed on your development machine:

*   **Node.js** (v18+)
*   **.NET 9.0 SDK**
*   **Python 3.10+**
*   **Git**

### Installation

1.  **Clone the repository**
    ```sh
    git clone https://github.com/ShawnTheCreator/kernalagent.git
    cd kernalagent
    ```

2.  **Setup the AI Microservice**
    ```sh
    cd Microservice
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Install dependencies
    pip install -r requirements.txt
    ```
    *   Create a `.env` file in `Microservice/` and add your keys (Gemini API, Firebase Service Account path).

3.  **Setup the Frontend**
    ```sh
    cd ../Frontend
    npm install
    ```
    *   Create a `.env.local` file with your Firebase and Supabase credentials.

4.  **Setup the Desktop App**
    *   Open `Desktop-App/Kernel Agent.sln` in Visual Studio 2022.
    *   Ensure "Kernel Agent" is the startup project.
    *   Add your `service-account.json` to the project root and set "Copy to Output Directory" to "Copy if newer".

5.  **Run the System**
    *   **Terminal 1 (Microservice):** `python app/main.py` (or `uvicorn app.main:app --reload`)
    *   **Terminal 2 (Frontend):** `npm run dev`
    *   **Visual Studio:** Press F5 to build and run the Desktop App.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

*   **Voice Commands**: Activate the agent with the wake word (configurable) or by clicking the orb. Try commands like "Open Notepad", "Check system health", or "Summarize this document".
*   **Agent Forge**: Use the "Forge" page in the desktop app to craft custom sub-agents with specific personalities and tool access.
*   **Dashboard**: Access the web dashboard (default `localhost:3000`) to view agent analytics, memory logs, and manage installed skills.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ARCHITECTURE -->
## Architecture

The system operates on a hub-and-spoke model:

*   **The Hub (Desktop App)**: The central nervous system. It handles user input (Voice/Text), renders the UI, and performs OS-level actions (File I/O, Window Management).
*   **The Brain (Microservice)**: A Python FastAPI server that processes complex requests. It handles LLM inference, runs computer vision tasks, and manages the state of long-running autonomous agents.
*   **The Cloud (Firebase/Supabase)**: Syncs user preferences, agent memory, and long-term history across devices.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [x] Initial WinUI 3 Desktop Interface
- [x] Python Microservice with Gemini Integration
- [x] Basic Voice Command Execution
- [ ] **Advanced Vision**: Real-time screen context understanding
- [ ] **Agent Marketplace**: Community-driven agent sharing
- [ ] **Deep OS Integration**: More granular control over Windows settings and registry
- [ ] **Multi-turn Conversation**: Improved context retention for complex tasks

See the [open issues](https://github.com/ShawnTheCreator/kernalagent/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

Shawn - [@ShawnTheCreator](https://github.com/ShawnTheCreator)

Project Link: [https://github.com/ShawnTheCreator/kernalagent](https://github.com/ShawnTheCreator/kernalagent)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[DotNet-badge]: https://img.shields.io/badge/.NET%209.0-512BD4?style=for-the-badge&logo=dotnet&logoColor=white
[DotNet-url]: https://dotnet.microsoft.com/
[Python-badge]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white
[Next-url]: https://nextjs.org/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[TailwindCSS-badge]: https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white
[TailwindCSS-url]: https://tailwindcss.com/
