/**
 * AudioVisualizer class handles the creation and management of an audio waveform visualization
 * using the Web Audio API and Canvas API.
 */
export function setupAudioVisualizer(canvasId) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');

  let analyser = null;
  let animationId = null;

  // Configuration
  const FFT_SIZE = 2048;
  const SMOOTHING_TIME_CONSTANT = 0.85;

  function initializeAnalyser(audioContext) {
    if (!analyser) {
      analyser = audioContext.createAnalyser();
      analyser.fftSize = FFT_SIZE;
      analyser.smoothingTimeConstant = SMOOTHING_TIME_CONSTANT;
    }
    return analyser;
  }

  function connectSource(source) {
    // Initialize or reset analyser
    const analyser = initializeAnalyser(source.context);

    // Connect the source to the analyser
    source.connect(analyser);

    // Start visualization if not already running
    if (!animationId) {
      draw();
    }
  }

  function draw() {
    if (!analyser) {
      animationId = requestAnimationFrame(draw);
      return;
    }

    // Get frequency data
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    // Clear canvas with white background
    ctx.fillStyle = 'rgb(255, 255, 255)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Setup line style
    ctx.strokeStyle = canvasId === 'aiVisualizer' ? '#6495ED' : '#8FBC8F';  // Different colors for AI vs Mic
    ctx.lineWidth = 3;
    ctx.beginPath();

    // Calculate width for each data point
    const sliceWidth = canvas.width / bufferLength;
    let x = 0;

    // Draw waveform
    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;  // Normalize to [-1, 1] range

      // Create tapering effect with enhanced center peak
      const progress = i / bufferLength;
      const amplitude = Math.pow(Math.sin(progress * Math.PI), 0.7);
      const y = ((v - 1) * amplitude * canvas.height / 2) + canvas.height / 2;

      // Draw line segments
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        // Use quadratic curves for smoother lines
        const prevX = x - sliceWidth;
        const prevY = calculatePreviousY(dataArray[i - 1], i - 1, bufferLength);
        const cpX = x - sliceWidth / 2;
        const cpY = (y + prevY) / 2;
        ctx.quadraticCurveTo(cpX, cpY, x, y);
      }

      x += sliceWidth;
    }

    // Add and reset shadow effect
    ctx.shadowColor = canvasId === 'aiVisualizer' ? 'rgba(74, 144, 226, 0.2)' : 'rgba(0, 128, 0, 0.2)';
    ctx.shadowBlur = 5;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Schedule next frame
    animationId = requestAnimationFrame(draw);
  }

  function calculatePreviousY(prevData, index, bufferLength) {
    const v = prevData / 128.0;
    const progress = index / bufferLength;
    const amplitude = Math.pow(Math.sin(progress * Math.PI), 0.7);
    return ((v - 1) * amplitude * canvas.height / 2) + canvas.height / 2;
  }

  function stop() {
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }

    if (analyser) {
      analyser.disconnect();
      analyser = null;
    }

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  // Handle canvas resize
  function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
  }

  // Set up resize observer
  const resizeObserver = new ResizeObserver(resizeCanvas);
  resizeObserver.observe(canvas.parentElement);

  // Initial resize
  resizeCanvas();

  return {
    connectSource,
    stop
  };
} 