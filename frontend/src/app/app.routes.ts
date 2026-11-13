import { Routes } from '@angular/router';
import { LandingComponent } from './pages/landing/landing.component';
import { CatalogComponent } from './pages/catalog/catalog.component';
import { SimulationStudioComponent } from './pages/simulation-studio/simulation-studio.component';
import { ComparisonComponent } from './pages/comparison/comparison.component';
import { EnduranceComponent } from './pages/endurance/endurance.component';

export const routes: Routes = [
  { path: '', component: LandingComponent },
  { path: 'catalog', component: CatalogComponent },
  { path: 'simulation', component: SimulationStudioComponent },
  { path: 'comparison', component: ComparisonComponent },
  { path: 'endurance', component: EnduranceComponent },
  { path: '**', redirectTo: '' }
];
