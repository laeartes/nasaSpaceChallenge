# NASA Space App Challenge

This repository contains the project created by Vytautė, Žygis, Jokūbas, and Mykolas for the NASA Space App Challenge Hackathon.

## About the Project

Our project was developed as part of the NASA Space App Challenge, focusing on solving real-world problems using space-related data and technology. Specifically, we are participating in the **[Build a Space Biology Knowledge Engine](https://www.spaceappschallenge.org/2025/challenges/build-a-space-biology-knowledge-engine/?tab=details)** challenge. 

This challenge aims to create a knowledge engine that organizes and makes space biology data accessible, enabling researchers and enthusiasts to explore and understand the effects of space on biological systems.

## What the Code Does

The code in this repository is designed to:
- Scrape and process space biology data from various sources.
- Provide an interactive web application for users to explore and analyze the data.
- Enable visualization of relationships between biological experiments, genes, and the effects of space conditions like microgravity and radiation.
- Support querying and filtering of data to help researchers find relevant information quickly.

## How to Install and Run the Project

Follow these steps to set up and run the project:

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd nasaSpaceChallenge
   ```

2. **Install Dependencies**
   Make sure you have Python installed. Then, install the required dependencies using pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**
   Start the FastAPI application using Uvicorn:
   ```bash
   python -m uvicorn app:app --reload
   ```
   The application will be available at `http://127.0.0.1:8000`.


## Team Members

- Vytautė
- Žygis
- Jokūbas
- Mykolas

## License

This project is open-source and available under the [MIT License](LICENSE).

---

*Created during the NASA Space App Challenge Hackathon.*

