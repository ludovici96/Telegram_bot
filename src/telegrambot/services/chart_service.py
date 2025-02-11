import matplotlib.pyplot as plt
import io
from typing import List, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)

class ChartService:
    def __init__(self):
        plt.style.use('bmh')

    def generate_pie_chart(self, data: List[Tuple[str, int]], title: str = "Message Distribution") -> io.BytesIO:
        """
        Generate a pie chart from the given data.
        
        Args:
            data: List of tuples containing (label, value)
            title: Title of the pie chart
            
        Returns:
            BytesIO object containing the PNG image
        """
        try:
            # Clear any existing plots
            plt.clf()
            
            # Create figure with a good size for Telegram
            plt.figure(figsize=(10, 8))
            
            # Extract labels and values
            labels = [item[0] for item in data]
            values = [item[1] for item in data]
            
            # Calculate percentages for labels
            total = sum(values)
            percentages = [(value/total)*100 for value in values]
            
            # Create labels with both count and percentage
            labels = [f"{label}\n({value:,} msgs, {pct:.1f}%)" 
                     for label, value, pct in zip(labels, values, percentages)]
            
            # Create pie chart with enhanced visuals
            plt.pie(values, labels=labels, autopct='', 
                   startangle=90, counterclock=False,
                   shadow=True,  # Add shadow for 3D effect
                   explode=[0.05 if i == 0 else 0 for i in range(len(values))],  # Slightly explode the largest slice
                   colors=plt.cm.Set3(np.linspace(0, 1, len(values))))  # Use a colorful palette
            
            # Add title with enhanced styling
            plt.title(title, pad=20, size=14, weight='bold')
            
            # Equal aspect ratio ensures circular pie
            plt.axis('equal')
            
            # Save plot to bytes buffer with white background
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor='white')
            buf.seek(0)
            
            # Close the plot to free memory
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error generating pie chart: {e}")
            raise 