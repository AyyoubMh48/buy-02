import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MediaManager } from './media-manager';

describe('MediaManager', () => {
  let component: MediaManager;
  let fixture: ComponentFixture<MediaManager>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MediaManager],
    }).compileComponents();

    fixture = TestBed.createComponent(MediaManager);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
