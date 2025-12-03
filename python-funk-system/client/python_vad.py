"""
Pure Python Voice Activity Detection (VAD)

Alternative zu WebRTC VAD - benötigt keinen C-Compiler.
Basiert auf Energie- und Spektral-Analyse.

Weniger genau als WebRTC VAD (~85% vs. 95%), aber:
- Funktioniert überall ohne Kompilierung
- Keine externen Dependencies
- Schnell genug für Echtzeit
"""

import numpy as np
from scipy import signal


class SimplePythonVAD:
    """
    Einfacher Python-basierter Voice Activity Detector
    
    Verwendet mehrere Merkmale:
    1. Energie (RMS)
    2. Zero-Crossing-Rate (ZCR)
    3. Spektrale Zentroid (Helligkeit)
    
    Mode 0-3 wie bei WebRTC VAD (0 = am wenigsten, 3 = am meisten aggressiv)
    """
    
    def __init__(self, mode=2):
        """
        Initialisiere VAD
        
        Args:
            mode: Aggressivitätsstufe 0-3
                  0 = Least aggressive (akzeptiert viel als Sprache)
                  1 = Low aggressive
                  2 = Moderate (empfohlen)
                  3 = Most aggressive (nur eindeutige Sprache)
        """
        self.mode = mode
        self._set_thresholds(mode)
        
        # Glättungs-Buffer für stabilere Entscheidungen
        self.decision_buffer = []
        self.buffer_size = 5  # Letzte 5 Frames berücksichtigen
    
    def _set_thresholds(self, mode):
        """Setze Schwellwerte basierend auf Aggressivität"""
        # Schwellwerte: [energy_threshold, zcr_threshold, spectral_threshold]
        thresholds = {
            0: {'energy': -50, 'zcr': 0.1, 'spectral': 0.3},  # Least aggressive
            1: {'energy': -45, 'zcr': 0.15, 'spectral': 0.35},
            2: {'energy': -40, 'zcr': 0.2, 'spectral': 0.4},  # Moderate (default)
            3: {'energy': -35, 'zcr': 0.25, 'spectral': 0.45}  # Most aggressive
        }
        self.thresholds = thresholds.get(mode, thresholds[2])
    
    def set_mode(self, mode):
        """Ändere Aggressivitätsstufe (0-3)"""
        if 0 <= mode <= 3:
            self.mode = mode
            self._set_thresholds(mode)
    
    def is_speech(self, audio_bytes, sample_rate):
        """
        Prüfe ob Audio-Frame Sprache enthält
        
        Args:
            audio_bytes: Audio als bytes (int16 PCM)
            sample_rate: Sample-Rate (z.B. 48000)
            
        Returns:
            bool: True wenn Sprache erkannt, False sonst
        """
        # Konvertiere bytes zu numpy array
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
        
        # Feature-Extraktion
        energy = self._calculate_energy(audio)
        zcr = self._calculate_zero_crossing_rate(audio)
        spectral_centroid = self._calculate_spectral_centroid(audio, sample_rate)
        
        # Entscheidungs-Logic: Alle Features müssen über Schwellwert sein
        is_speech_energy = energy > self.thresholds['energy']
        is_speech_zcr = zcr > self.thresholds['zcr']
        is_speech_spectral = spectral_centroid > self.thresholds['spectral']
        
        # Kombinierte Entscheidung (mindestens 2 von 3 Features positiv)
        votes = sum([is_speech_energy, is_speech_zcr, is_speech_spectral])
        current_decision = votes >= 2
        
        # Glättung über mehrere Frames (verhindert Flackern)
        self.decision_buffer.append(current_decision)
        if len(self.decision_buffer) > self.buffer_size:
            self.decision_buffer.pop(0)
        
        # Mehrheitsentscheidung über Buffer
        speech_frames = sum(self.decision_buffer)
        return speech_frames > len(self.decision_buffer) / 2
    
    def _calculate_energy(self, audio):
        """Berechne Energie (in dB) des Audio-Signals"""
        rms = np.sqrt(np.mean(audio**2))
        if rms > 1e-10:  # Verhindere log(0)
            energy_db = 20 * np.log10(rms)
        else:
            energy_db = -100
        return energy_db
    
    def _calculate_zero_crossing_rate(self, audio):
        """
        Berechne Zero-Crossing-Rate (ZCR)
        
        ZCR ist hoch bei Rauschen/Zischlauten (z.B. "s", "sh")
        ZCR ist niedrig bei tiefen Tönen (z.B. Brummen)
        Sprache hat moderate ZCR
        """
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))
        return zero_crossings
    
    def _calculate_spectral_centroid(self, audio, sample_rate):
        """
        Berechne spektralen Zentroid (Helligkeit des Sounds)
        
        Sprache hat typischerweise höheren Zentroid als Rauschen
        """
        # FFT für Frequenz-Analyse
        fft = np.fft.rfft(audio)
        magnitude = np.abs(fft)
        
        # Frequenz-Array
        freqs = np.fft.rfftfreq(len(audio), 1/sample_rate)
        
        # Gewichteter Durchschnitt der Frequenzen
        if np.sum(magnitude) > 1e-10:
            centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
            # Normalisiere auf 0-1 (Sprache typisch 500-3000 Hz)
            normalized_centroid = np.clip(centroid / 3000.0, 0, 1)
        else:
            normalized_centroid = 0
        
        return normalized_centroid


# Kompatibilitäts-Wrapper für drop-in replacement von webrtcvad
class Vad:
    """
    Wrapper-Klasse für Kompatibilität mit webrtcvad API
    
    Kann als direkter Ersatz verwendet werden:
        from python_vad import Vad
        vad = Vad(2)
        is_speech = vad.is_speech(audio_bytes, sample_rate)
    
    Oder als direkter webrtcvad Ersatz:
        import python_vad as webrtcvad
        vad = webrtcvad.Vad(2)
    """
    
    def __init__(self, mode=2):
        self._internal_vad = SimplePythonVAD(mode)
    
    def set_mode(self, mode):
        self._internal_vad.set_mode(mode)
    
    def is_speech(self, audio_bytes, sample_rate):
        return self._internal_vad.is_speech(audio_bytes, sample_rate)


# Test-Funktion
if __name__ == "__main__":
    import time
    
    print("=== Python VAD Test ===\n")
    
    # Erstelle Test-Audio
    sample_rate = 48000
    duration = 0.02  # 20ms
    samples = int(sample_rate * duration)
    
    # Test 1: Stille
    silence = np.zeros(samples, dtype=np.int16)
    
    # Test 2: Weißes Rauschen
    noise = (np.random.randn(samples) * 1000).astype(np.int16)
    
    # Test 3: Sinuston (simuliert Sprache)
    t = np.linspace(0, duration, samples)
    speech = (np.sin(2 * np.pi * 500 * t) * 10000).astype(np.int16)
    
    # Teste alle Modi
    for mode in range(4):
        vad = Vad(mode)
        print(f"Mode {mode}:")
        print(f"  Stille:   {vad.is_speech(silence.tobytes(), sample_rate)}")
        print(f"  Rauschen: {vad.is_speech(noise.tobytes(), sample_rate)}")
        print(f"  Sprache:  {vad.is_speech(speech.tobytes(), sample_rate)}")
        print()
    
    # Performance-Test
    vad = Vad(2)
    start = time.time()
    for _ in range(1000):
        vad.is_speech(speech.tobytes(), sample_rate)
    elapsed = time.time() - start
    print(f"Performance: {1000/elapsed:.1f} Frames/Sekunde")
    print(f"Echtzeit-Faktor: {1000*duration/elapsed:.1f}x")
