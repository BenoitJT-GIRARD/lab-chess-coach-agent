import { ApplicationConfig } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(),
    // Les composants Angular Material (info-bulles, puces, indicateur de
    // loading) s'appuient sur le module d'animations.
    provideAnimations(),
  ],
};
