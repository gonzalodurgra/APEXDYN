import { Component, ElementRef, Input, OnChanges, SimpleChanges, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TrackGeometryPoint } from '../../models/types';

@Component({
  selector: 'app-track-map-viewer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './track-map-viewer.component.html',
  styleUrl: './track-map-viewer.component.css'
})
export class TrackMapViewerComponent implements AfterViewInit, OnChanges {
  @ViewChild('mapCanvas') mapCanvas!: ElementRef<HTMLCanvasElement>;
  @Input() points: TrackGeometryPoint[] = [];
  @Input() trackName = '';
  @Input() trackLengthM = 0;
  @Input() isClosedLoop = true;

  ngAfterViewInit(): void {
    this.drawTrack();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.mapCanvas && changes['points']) {
      this.drawTrack();
    }
  }

  private drawTrack(): void {
    if (!this.mapCanvas) return;
    const canvas = this.mapCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Resize canvas based on client bounding rect
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const width = rect.width;
    const height = rect.height;

    ctx.clearRect(0, 0, width, height);

    if (!this.points || this.points.length < 2) return;

    // Obtener rangos x_m, y_m
    const xs = this.points.map(p => p.x_m ?? 0);
    const ys = this.points.map(p => p.y_m ?? 0);

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;

    const padding = 35;
    const scale = Math.min((width - padding * 2) / rangeX, (height - padding * 2) / rangeY);

    const offsetX = (width - rangeX * scale) / 2;
    const offsetY = (height - rangeY * scale) / 2;

    const toScreen = (x: number, y: number) => ({
      x: offsetX + (x - minX) * scale,
      // Invertir Y porque en la pantalla el eje Y va hacia abajo
      y: height - (offsetY + (y - minY) * scale)
    });

    // Dibujar trazado
    ctx.beginPath();
    ctx.lineWidth = 3.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#00d2ff';
    ctx.shadowColor = 'rgba(0, 210, 255, 0.6)';
    ctx.shadowBlur = 12;

    const start = toScreen(xs[0], ys[0]);
    ctx.moveTo(start.x, start.y);

    for (let i = 1; i < this.points.length; i++) {
      const pt = toScreen(xs[i], ys[i]);
      ctx.lineTo(pt.x, pt.y);
    }

    if (this.isClosedLoop) {
      ctx.closePath();
    }
    ctx.stroke();

    // Dibujar línea de meta / salida
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#ff3344';
    ctx.beginPath();
    ctx.arc(start.x, start.y, 5, 0, Math.PI * 2);
    ctx.fill();

    // Etiqueta Salida
    ctx.fillStyle = '#ffffff';
    ctx.font = '10px JetBrains Mono';
    ctx.fillText('FINISH / START', start.x + 8, start.y - 6);
  }
}
