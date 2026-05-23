data = [2, 4, 6, 8, 10]
average = sum(data) / len(data)
print("Average:", average)
import matplotlib.pyplot as plt

plt.plot(data)
plt.title("AI Learning Trend")
plt.xlabel("Index")
plt.ylabel("Value")
plt.savefig("ai_trend.png")