describe('Home Page', () => {
  beforeEach(() => {
    cy.visit('http://localhost:4201');
  });

  it('should display the home page title', () => {
    cy.get('h1').should('contain', 'Home page');
  });

  it('should display the lorem ipsum text', () => {
    cy.get('p').should('contain', 'Lorem ipsum dolor sit amet');
  });

  it('should have a primary button', () => {
    cy.get('button[mat-raised-button]')
      .should('be.visible')
      .and('contain', 'Click me');
  });

  it('should be able to click the button', () => {
    cy.get('button[mat-raised-button]').click();
  });

  it('should be able to toggle the checkbox', () => {
    cy.get('mat-checkbox').click();
    cy.get('mat-checkbox input[type="checkbox"]').should('be.checked');
    
    cy.get('mat-checkbox').click();
    cy.get('mat-checkbox input[type="checkbox"]').should('not.be.checked');
  });

  it('should have proper spacing and layout', () => {
    cy.get('.space-y-4').should('exist');
    cy.get('.flex.items-center.gap-4').should('exist');
  });
});
