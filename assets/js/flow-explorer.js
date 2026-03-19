document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("analyze-button");
  const result = document.getElementById("tool-result");

  if (!button || !result) return;

  button.addEventListener("click", () => {
    const commodity = document.getElementById("commodity").value;
    const func = document.getElementById("function").value;

    let text = "";

    if (commodity === "lng" && func === "routing") {
      text = "Singapore becomes relevant through LNG routing because it helps structure Asian maritime energy movement through continuity, coordination, and port-linked operational density.";
    } else if (commodity === "bunkering-fuel" && func === "bunkering") {
      text = "Singapore's bunkering significance lies in its ability to sustain large-scale maritime continuity. This is a form of logistical sovereignty.";
    } else if (func === "coordination") {
      text = "Singapore matters where commodity systems require synchronization between movement, infrastructure, timing, and commercial trust.";
    } else {
      text = "Singapore's strategic relevance emerges when movement must be organized at scale, with continuity and operational reliability.";
    }

    result.textContent = text;
  });
});
