# CleanEnergyBot

## Overview

The CleanEnergyBot is a Telegram bot designed to empower users in Ireland with real-time insights into electricity usage, CO2 emissions forecasts, and energy-saving recommendations. Utilizing real-time data from EirGrid, the entity responsible for electricity delivery across Ireland, this bot leverages advanced data analysis techniques and the capabilities of GPT-3 to provide actionable energy usage insights. By comparing current CO2 emissions forecasts with previous data and EU standard rates, the CleanEnergyBot aims to assist users in making informed, environmentally friendly energy decisions.

![Real-time Data Scraping Diagram](/images/overview.png)

[🎥 Watch the video on how to use the bot](https://www.youtube.com/watch?v=qxA-Xx5oGXI)

## Features

- **Real-time Electricity Insights**: Provides up-to-the-minute data on electricity usage and CO2 emissions in Ireland.
- **CO2 Emissions Forecasts**: Offers forecasts of CO2 emissions, enabling users to compare current data with past performance and EU standards.
- **Energy Saving Recommendations**: Delivers tailored advice on the most efficient times for energy usage, helping users reduce their carbon footprint.
- **Text-to-Speech for Energy Saving Tips**: Utilising the ElevenLabs API, the bot now sends energy-saving tips as voice messages, making it easier and more convenient for users to receive and listen to advice on the go.
- **User Interaction**: Supports various commands for users to start conversations, receive energy status updates, give feedback, and more.
- **Graphical Analysis**: Sends users a color-coded graphical image indicating periods of low, medium, and high carbon intensity.

## Development

The CleanEnergyBot was developed through a series of carefully structured steps, incorporating data fetching, analysis, and user interaction mechanisms:

1. **Data Collection**: A Python script was created to fetch real-time and historical electricity data from EirGrid.
2. **Data Analysis**: The fetched data are analyzed to determine CO2 emissions intensity and compliance with EU standards, categorizing them into low, medium, and high segments.
3. **OpenAI API Integration**: Functions were developed to prepare structured prompts for the OpenAI API, facilitating the generation of reports and energy-saving tips for users.
4. **Text-to-Speech Integration**: The ElevenLabs API has been integrated to convert energy-saving tips into audio format, enhancing accessibility and user engagement.
5. **Interactive Bot Interface**: The bot offers various interaction options, including restarting the conversation, contacting the developer, and providing feedback.

## Deployment on Azure

The application is deployed on Azure using Azure Container Apps, leveraging Azure's cloud infrastructure for high availability and performance. The deployment process includes:

1. **Containerization** using Docker to ensure portability.
2. **Azure Container Registry** for securely storing Docker images.
3. **Azure Container App** for deploying and managing the application in a serverless environment.
4. **CI/CD Pipeline** with GitHub Actions for automated testing, building, and deployment from GitHub to Azure.
5. **Environment Configuration** using GitHub Secrets and Azure's tools to manage sensitive information securely.

## Getting Started

To test or contribute to CleanEnergyBot, follow these steps:

1. **Clone the Repository**: Clone the project to your local machine using the following command:
   `git clone https://github.com/SaM-92/telegram-energy-api.git`

2. **Set Up Environment**: Navigate to the cloned repository directory and use the `requirements.txt` file to set up your Python environment with the necessary dependencies by running: `pip install -r requirements.txt`

3. **Configuration**: Securely store sensitive information and API tokens by setting them as environment variables in a .env file. Replace `your_token` with your actual tokens for each variable:
   `OPENAI_API_KEY=your token`,
   `Telegram_energy_api=your tiokne`,
   `CHANNEL_ID_FOR_FEEDBACK=your token`,
   `ELEVEN_API_KEY=your token`

4. **Run Locally**: Test the bot locally by running the provided application script: `python main.py`

Then, open Telegram and go to your bot to see its operations. Be careful; you need to create a bot first in Telegram using BotFather and pass its token to the script (as the `Telegram_energy_api` environment variable) for it to work.

## Contributing

Contributions are welcome! Please ensure your pull requests are well-documented and tested. Adherence to coding standards, including the use of docstrings and comments, is encouraged.

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the [LICENSE](https://www.gnu.org/licenses/agpl-3.0.en.html) file for details. Contributions must adhere to the same license, ensuring all derived projects remain open source.

## Contact

For feedback, inquiries, or further information, please contact:

- Email: 📧 sam.misaqian@gmail.com
- GitHub: 💻 https://github.com/SaM-92
- LinkedIn: 🔗 https://www.linkedin.com/in/saeed-misaghian/
