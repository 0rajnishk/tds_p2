# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas",
#   "seaborn",
#   "matplotlib",
#   "requests",
#   "scikit-learn"
# ]
# ///

import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests
import json
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def get_api_details():
    """
    Retrieves the AI Proxy token and sets the API endpoint URL.
    """
    api_proxy_token = os.getenv("AIPROXY_TOKEN")
    if not api_proxy_token:
        print("Error: AIPROXY_TOKEN environment variable not set.")
        sys.exit(1)
    
    api_proxy_url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    return api_proxy_token, api_proxy_url

def detect_encoding(file_path):
    """
    Detects the encoding of a file using chardet.
    """
    try:
        import chardet
    except ImportError:
        print("chardet library not found. Installing...")
        os.system("pip install chardet")
        import chardet
    
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

def analyze_dataset(file_path):
    """
    Loads the dataset with appropriate encoding and performs basic and advanced analysis.
    Returns the DataFrame and a dictionary containing analysis details.
    """
    # Detect encoding
    encoding = detect_encoding(file_path)
    try:
        df = pd.read_csv(file_path, encoding=encoding)
        print(f"Successfully loaded {file_path} with encoding {encoding}")
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        sys.exit(1)
    
    # Basic Analysis
    try:
        summary_stats = df.describe(include='all').to_dict()
    except Exception as e:
        print(f"Warning: Unable to generate summary statistics for {file_path}. {e}")
        summary_stats = {}
    
    missing_values = df.isnull().sum().to_dict()
    dtypes = df.dtypes.apply(str).to_dict()
    columns = list(df.columns)
    
    analysis = {
        "columns": columns,
        "dtypes": dtypes,
        "missing_values": missing_values,
        "summary_stats": summary_stats
    }
    
    # Advanced Analysis: Outlier Detection
    numeric_cols = df.select_dtypes(include=['number']).columns
    outliers = {}
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outlier_count = df[(df[col] < lower_bound) | (df[col] > upper_bound)].shape[0]
        outliers[col] = outlier_count
    
    analysis["outliers"] = outliers
    
    # Clustering (if applicable)
    if len(numeric_cols) >= 2:
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(df[numeric_cols].dropna())
        kmeans = KMeans(n_clusters=3, random_state=42)
        clusters = kmeans.fit_predict(scaled_data)
        df['Cluster'] = clusters
        cluster_counts = df['Cluster'].value_counts().to_dict()
        analysis["clusters"] = cluster_counts
    else:
        analysis["clusters"] = "Not enough numeric columns for clustering."
    
    return df, analysis

def generate_visualizations(df, output_dir):
    """
    Generates visualizations based on the DataFrame and saves them as PNG files.
    Returns a list of generated PNG filenames.
    """
    png_files = []
    
    # 1. Correlation Heatmap (if applicable)
    numeric_columns = df.select_dtypes(include='number').columns
    if len(numeric_columns) > 1:
        corr = df[numeric_columns].corr()
        plt.figure(figsize=(12, 10))
        sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
        plt.title("Correlation Heatmap")
        heatmap_path = os.path.join(output_dir, "correlation_heatmap.png")
        plt.savefig(heatmap_path)
        plt.close()
        png_files.append("correlation_heatmap.png")
        print(f"Saved correlation_heatmap.png in {output_dir}")
    
    # 2. Distribution Plot of the First Numeric Column
    if len(numeric_columns) > 0:
        first_numeric = numeric_columns[0]
        plt.figure(figsize=(10, 6))
        sns.histplot(df[first_numeric].dropna(), kde=True, bins=30, color='skyblue')
        plt.title(f"Distribution of {first_numeric}")
        plt.xlabel(first_numeric)
        plt.ylabel("Frequency")
        dist_path = os.path.join(output_dir, f"{first_numeric}_distribution.png")
        plt.savefig(dist_path)
        plt.close()
        png_files.append(f"{first_numeric}_distribution.png")
        print(f"Saved {first_numeric}_distribution.png in {output_dir}")
    
    # 3. Categorical Count Plot (if applicable)
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns
    if len(categorical_columns) > 0:
        first_categorical = categorical_columns[0]
        plt.figure(figsize=(12, 8))
        sns.countplot(
            data=df,
            y=first_categorical,
            order=df[first_categorical].value_counts().index[:10],
            palette="viridis",
            hue=first_categorical,
            dodge=False
        )
        plt.title(f"Top 10 {first_categorical} Categories")
        plt.xlabel("Count")
        plt.ylabel(first_categorical)
        plt.legend([], [], frameon=False)  # Hide legend to fix FutureWarning
        count_path = os.path.join(output_dir, f"{first_categorical}_count.png")
        plt.savefig(count_path)
        plt.close()
        png_files.append(f"{first_categorical}_count.png")
        print(f"Saved {first_categorical}_count.png in {output_dir}")
    
    return png_files

def suggest_additional_analyses(analysis):
    """
    Uses the LLM to suggest additional analyses based on the current analysis.
    Returns a list of suggested analyses.
    """
    suggestions = []
    if analysis["outliers"]:
        suggestions.append("Performing outlier detection to identify anomalies in the data.")
    if analysis["clusters"] and isinstance(analysis["clusters"], dict):
        suggestions.append("Conducting clustering analysis to find natural groupings within the data.")
    return suggestions

def narrate_story(analysis, png_files, api_proxy_token, api_proxy_url):
    """
    Generates a narrative in Markdown format using the LLM based on the analysis.
    Returns the narrative as a string.
    """
    # Create a concise summary to send to the LLM
    analysis_summary = (
        f"**Columns:** {analysis['columns']}\n"
        f"**Data Types:** {analysis['dtypes']}\n"
        f"**Missing Values:** {analysis['missing_values']}\n"
        f"**Summary Statistics:** {list(analysis['summary_stats'].keys())}\n"
        f"**Outliers Detected:** {analysis['outliers']}\n"
        f"**Clustering Results:** {analysis['clusters']}\n"
    )
    
    # Define the prompt for the LLM
    prompt = (
        "You are a data scientist. Based on the analysis provided below, write a detailed narrative in Markdown format that includes:\n"
        "1. A brief description of the dataset and its structure.\n"
        "2. Key insights and interesting findings.\n"
        "3. Descriptions of the generated charts and their significance.\n"
        "4. Potential implications or recommended actions based on the findings.\n"
        "5. Suggestions for additional analyses that could provide further insights.\n\n"
        f"**Analysis:**\n{analysis_summary}"
    )
    
    # Prepare the payload for the AI Proxy
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful data scientist narrating the story of a dataset."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500,
        "temperature": 0.7
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_proxy_token}"
    }
    
    try:
        response = requests.post(api_proxy_url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            story = result['choices'][0]['message']['content']
            print("Successfully generated narrative with LLM.")
        else:
            print(f"Error: {response.status_code}, {response.text}")
            story = f"Error generating narrative: {response.status_code}, {response.text}"
    except Exception as e:
        print(f"Error generating narrative: {e}")
        story = f"Error generating narrative: {e}"
    
    # Append image references to the narrative
    if png_files and "error" not in story.lower():
        story += "\n\n## Visualizations\n"
        for img in png_files:
            story += f"![{img}]({img})\n"
    
    return story

def analyze_and_generate_output(file_path, api_proxy_token, api_proxy_url):
    """
    Processes a single CSV file: analyzes data, generates visualizations, narrates the story.
    Saves outputs in a dedicated directory.
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = os.path.join(".", base_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created directory: {output_dir}")
    
    df, analysis = analyze_dataset(file_path)
    png_files = generate_visualizations(df, output_dir)
    story = narrate_story(analysis, png_files, api_proxy_token, api_proxy_url)
    
    # Write story to README.md
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w", encoding='utf-8') as f:
        f.write(story)
    print(f"Saved README.md in {output_dir}")
    
    return output_dir

def main():
    """
    Main function to process all provided CSV files.
    """
    if len(sys.argv) < 2:
        print("Usage: uv run autolysis.py dataset1.csv dataset2.csv ...")
        sys.exit(1)
    
    file_paths = sys.argv[1:]
    api_proxy_token, api_proxy_url = get_api_details()
    output_dirs = []
    
    for file_path in file_paths:
        if os.path.exists(file_path):
            print(f"Processing file: {file_path}")
            output_dir = analyze_and_generate_output(file_path, api_proxy_token, api_proxy_url)
            output_dirs.append(output_dir)
        else:
            print(f"File {file_path} not found!")
    
    print(f"Analysis completed. Results saved in directories: {', '.join(output_dirs)}")

if __name__ == "__main__":
    main()
