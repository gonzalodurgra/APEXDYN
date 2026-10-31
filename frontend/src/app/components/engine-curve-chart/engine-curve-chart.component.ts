import { Component, ElementRef, Input, OnChanges, SimpleChanges, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-engine-curve-chart',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './engine-curve-chart.component.html',
  styleUrl: './engine-curve-chart.component.css'
})
export class EngineCurveChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;
  @Input() curvePoints: { rpm: number; torque_nm: number; power_kw: number }[] = [];
  @Input() maxPowerKw = 0;
  @Input() maxTorqueNm = 0;

  private chart: Chart | null = null;

  ngAfterViewInit(): void {
    this.createOrUpdateChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.chartCanvas && (changes['curvePoints'] || changes['maxPowerKw'])) {
      this.createOrUpdateChart();
    }
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.destroy();
    }
  }

  private createOrUpdateChart(): void {
    if (!this.chartCanvas) return;
    if (this.chart) {
      this.chart.destroy();
    }

    const points = this.curvePoints && this.curvePoints.length > 0 
      ? [...this.curvePoints].sort((a, b) => a.rpm - b.rpm)
      : this.generateSyntheticCurve();

    const labels = points.map(p => p.rpm);
    const torqueData = points.map(p => p.torque_nm);
    // Convertir kW a CV (1 kW ≈ 1.35962 CV)
    const powerHpData = points.map(p => p.power_kw ? +(p.power_kw * 1.35962).toFixed(1) : +(p.torque_nm * p.rpm / 9548.8 * 1.35962).toFixed(1));

    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Par Motor (Nm)',
            data: torqueData,
            borderColor: '#00d2ff',
            backgroundColor: 'rgba(0, 210, 255, 0.1)',
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            yAxisID: 'yTorque',
            pointRadius: 2,
            pointHoverRadius: 6,
            pointBackgroundColor: '#00d2ff',
          },
          {
            label: 'Potencia (CV)',
            data: powerHpData,
            borderColor: '#ff3344',
            backgroundColor: 'rgba(255, 51, 68, 0.12)',
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            yAxisID: 'yPower',
            pointRadius: 2,
            pointHoverRadius: 6,
            pointBackgroundColor: '#ff3344',
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(11, 15, 23, 0.95)',
            borderColor: 'rgba(255, 255, 255, 0.15)',
            borderWidth: 1,
            titleFont: { family: 'JetBrains Mono', size: 12 },
            bodyFont: { family: 'Inter', size: 12 },
            padding: 10,
            callbacks: {
              title: (items) => `${items[0].label} RPM`,
              label: (context) => {
                const label = context.dataset.label || '';
                const val = context.parsed.y;
                return ` ${label}: ${val}`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#94a3b8',
              font: { family: 'JetBrains Mono', size: 10 }
            }
          },
          yTorque: {
            type: 'linear',
            position: 'left',
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#00d2ff',
              font: { family: 'JetBrains Mono', size: 10 },
              callback: (val) => `${val} Nm`
            }
          },
          yPower: {
            type: 'linear',
            position: 'right',
            grid: { display: false },
            ticks: {
              color: '#ff3344',
              font: { family: 'JetBrains Mono', size: 10 },
              callback: (val) => `${val} CV`
            }
          }
        }
      }
    };

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (ctx) {
      this.chart = new Chart(ctx, config);
    }
  }

  private generateSyntheticCurve() {
    const pKw = this.maxPowerKw || 375;
    const tNm = this.maxTorqueNm || 470;
    const idle = 1000;
    const redline = 9000;
    const points = [];
    for (let r = idle; r <= redline; r += 500) {
      const frac = (r - idle) / (redline - idle);
      const torque = tNm * (0.65 + 0.35 * Math.sin(frac * Math.PI));
      const powerKw = (torque * r) / 9548.8;
      points.push({ rpm: r, torque_nm: Math.round(torque), power_kw: Math.round(powerKw) });
    }
    return points;
  }
}
