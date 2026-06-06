document.addEventListener("DOMContentLoaded", () => {
  console.log("Dashboard.js loaded");
  document.body.style.overflow = 'auto';
  document.documentElement.style.scrollBehavior = 'auto';
  if (typeof Chart === 'undefined') {
    console.error("Chart.js not loaded!");
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
    script.onload = () => {
      console.log("Chart.js loaded dynamically");
      initializeDashboard();
    };
    document.head.appendChild(script);
    return;
  }

  initializeDashboard();

  function initializeDashboard() {
    function safeGetData(id, fallback = []) {
      try {
        const element = document.getElementById(id);
        if (!element) {
          console.warn(`Element ${id} not found`);
          return fallback;
        }
        const data = JSON.parse(element.textContent || element.innerHTML);
        return data;
      } catch (e) {
        console.error(`Error parsing ${id}:`, e);
        return fallback;
      }
    }

    const trendLabels = safeGetData("labels-data", []);
    const overallScores = safeGetData("scores-data", []);
    const avgScores = safeGetData("avg-data", {});
    const issueLabels = safeGetData("issue-labels", []);
    const issueValues = safeGetData("issue-values", []);
    const sentiments = safeGetData("sentiments-data", []);
    const grammarCounts = safeGetData("grammar-data", []);
    const topicRelevance = safeGetData("topic-data", {});

    console.log("Dashboard data loaded:", {
      trendLabels: trendLabels.length,
      overallScores: overallScores.length,
      avgScores: Object.keys(avgScores).length,
      issueLabels: issueLabels.length,
      issueValues: issueValues.length,
      sentiments: sentiments.length,
      grammarCounts: grammarCounts.length,
      topicRelevance: Object.keys(topicRelevance).length
    });
    function createChart(canvasId, config) {
      try {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
          console.error(`Canvas ${canvasId} not found`);
          return;
        }
        const container = canvas.parentElement;
        if (container) {
          canvas.style.display = 'block';
          canvas.width = container.offsetWidth || 400;
          canvas.height = container.offsetHeight || 300;
        }

        const ctx = canvas.getContext("2d");        
        if (window[canvasId + '_chart']) {
          window[canvasId + '_chart'].destroy();
        }

        const chart = new Chart(ctx, config);
        window[canvasId + '_chart'] = chart;
        console.log(`Chart ${canvasId} created successfully`);
        
        return chart;
      } catch (error) {
        console.error(`Error creating chart ${canvasId}:`, error);
        return null;
      }
    }
    const fallbackLabels = ["Essay 1", "Essay 2", "Essay 3", "Essay 4", "Essay 5"];
    const fallbackScores = [75, 82, 68, 91, 77];
    const fallbackAvgScores = {
      "Grammar": 78,
      "Readability": 82,
      "Sentiment": 75,
      "Topic Relevance": 85
    };
    const finalTrendLabels = trendLabels.length > 0 ? trendLabels : fallbackLabels;
    const finalOverallScores = overallScores.length > 0 ? overallScores : fallbackScores;
    const finalAvgScores = Object.keys(avgScores).length > 0 ? avgScores : fallbackAvgScores;
    createChart("scoreTrend", {
      type: "line",
      data: {
        labels: finalTrendLabels,
        datasets: [{
          label: "Overall Score",
          data: finalOverallScores,
          fill: false,
          tension: 0.25,
          borderColor: "#3b82f6",
          backgroundColor: "#3b82f6",
          borderWidth: 2,
          pointBackgroundColor: "#3b82f6",
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
          pointRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        scales: { 
          y: { 
            min: 0, 
            max: 100,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          },
          x: {
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top'
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white'
          }
        }
      }
    });
    createChart("avgScores", {
      type: "bar",
      data: {
        labels: Object.keys(finalAvgScores),
        datasets: [{
          label: "Average Score",
          data: Object.values(finalAvgScores),
          backgroundColor: "#10b981",
          borderColor: "#059669",
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        scales: { 
          x: { 
            min: 0, 
            max: 100,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          },
          y: {
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top'
          }
        }
      }
    });
    if (issueLabels.length > 0 && issueValues.length > 0) {
      createChart("issuesChart", {
        type: "doughnut",
        data: {
          labels: issueLabels,
          datasets: [{
            data: issueValues,
            backgroundColor: ["#ef4444", "#3b82f6", "#f59e0b", "#10b981", "#8b5cf6", "#f97316"],
            borderWidth: 2,
            borderColor: "#ffffff"
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { 
            legend: { 
              position: "bottom",
              labels: {
                padding: 15,
                usePointStyle: true
              }
            }
          }
        }
      });
    } else {
      console.log("No data for issues chart - using placeholder");
      const issuesContainer = document.getElementById("issuesChart");
      if (issuesContainer) {
        issuesContainer.parentElement.innerHTML = "<p class='text-center text-gray-500'>No issues data available</p>";
      }
    }
    if (trendLabels.length > 0 && sentiments.length > 0) {
      createChart("sentimentTrend", {
        type: "line",
        data: {
          labels: trendLabels,
          datasets: [{
            label: "Positivity Score",
            data: sentiments,
            borderColor: "#8b5cf6",
            backgroundColor: "rgba(139, 92, 246, 0.1)",
            fill: true,
            tension: 0.25,
            borderWidth: 2,
            pointBackgroundColor: "#8b5cf6",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { 
            y: { 
              min: 0, 
              max: 100,
              grid: {
                color: 'rgba(0, 0, 0, 0.1)'
              }
            },
            x: {
              grid: {
                color: 'rgba(0, 0, 0, 0.1)'
              }
            }
          },
          plugins: {
            legend: {
              display: true,
              position: 'top'
            }
          }
        }
      });
    } else {
      console.log("No data for sentiment chart");
    }
    if (trendLabels.length > 0 && grammarCounts.length > 0) {
      createChart("grammarTrend", {
        type: "bar",
        data: {
          labels: trendLabels,
          datasets: [{
            label: "Grammar Issues Count",
            data: grammarCounts,
            backgroundColor: "#ef4444",
            borderColor: "#dc2626",
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { 
            y: { 
              beginAtZero: true,
              grid: {
                color: 'rgba(0, 0, 0, 0.1)'
              }
            },
            x: {
              grid: {
                color: 'rgba(0, 0, 0, 0.1)'
              }
            }
          },
          plugins: {
            legend: {
              display: true,
              position: 'top'
            }
          }
        }
      });
    } else {
      console.log("No data for grammar chart");
    }
    if (Object.keys(topicRelevance).length > 0) {
      const topicLabels = Object.keys(topicRelevance);
      const topicData = Object.values(topicRelevance);
      
      createChart("topicRelevanceChart", {
        type: "pie",
        data: {
          labels: topicLabels,
          datasets: [{
            data: topicData,
            backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
            borderWidth: 2,
            borderColor: "#ffffff"
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { 
            legend: { 
              position: "bottom",
              labels: {
                padding: 15,
                usePointStyle: true
              }
            }
          }
        }
      });
    } else {
      console.log("No data for topic relevance chart");
    }
    window.addEventListener('resize', () => {
      Object.keys(window).forEach(key => {
        if (key.includes('_chart') && window[key] && typeof window[key].resize === 'function') {
          window[key].resize();
        }
      });
    });

    console.log("Dashboard initialization complete");
  }
});