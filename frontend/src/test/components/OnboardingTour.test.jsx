import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

vi.mock('../../context/AuthContext', () => ({
    useAuth: vi.fn(() => ({ isLoggedIn: true })),
}));

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }) => <div {...props}>{children}</div>,
        button: ({ children, ...props }) => <button {...props}>{children}</button>,
    },
    AnimatePresence: ({ children }) => <>{children}</>,
}));

vi.mock('lucide-react', () => ({
    X: ({ ...props }) => <span {...props}>X</span>,
    ChevronRight: (props) => <span {...props}>chevron</span>,
}));

describe('OnboardingTour', () => {
    beforeEach(async () => {
        localStorage.clear();
        const { useAuth } = await import('../../context/AuthContext');
        useAuth.mockReset();
        useAuth.mockReturnValue({ isLoggedIn: true });
    });

    async function getComponent() {
        return (await import('../../components/OnboardingTour')).default;
    }

    it('renders when user is logged in and onboarding not completed', async () => {
        const OnboardingTour = await getComponent();
        render(<OnboardingTour />);
        await waitFor(() => {
            expect(screen.getByText(/Welcome to ScholarForm/)).toBeInTheDocument();
        });
    });

    it('does not render when onboarding is completed', async () => {
        localStorage.setItem('onboarding_completed', 'true');
        const OnboardingTour = await getComponent();
        const { container } = render(<OnboardingTour />);
        await waitFor(() => {
            expect(container.innerHTML).toBe('');
        });
    });

    it('does not render for unauthenticated users', async () => {
        const { useAuth } = await import('../../context/AuthContext');
        useAuth.mockReturnValue({ isLoggedIn: false });

        const OnboardingTour = await getComponent();
        const { container } = render(<OnboardingTour />);
        await waitFor(() => {
            expect(container.innerHTML).toBe('');
        });
    });

    it('navigates to next step', async () => {
        const OnboardingTour = await getComponent();
        render(<OnboardingTour />);
        await waitFor(() => {
            expect(screen.getByText('Next')).toBeInTheDocument();
        });
        fireEvent.click(screen.getByText('Next'));
        await waitFor(() => {
            expect(screen.getByText('Easy Upload')).toBeInTheDocument();
        });
    });

    it('shows Finish on last step', async () => {
        const OnboardingTour = await getComponent();
        render(<OnboardingTour />);
        await waitFor(() => {
            expect(screen.getByText('Next')).toBeInTheDocument();
        });
        for (let i = 0; i < 4; i++) {
            fireEvent.click(screen.getByText('Next'));
            await vi.waitFor(() => {});
        }
        await waitFor(() => {
            expect(screen.getByText('Finish')).toBeInTheDocument();
        });
    });

    it('shows Back button after first step', async () => {
        const OnboardingTour = await getComponent();
        render(<OnboardingTour />);
        await waitFor(() => {
            expect(screen.getByText('Next')).toBeInTheDocument();
        });
        fireEvent.click(screen.getByText('Next'));
        await waitFor(() => {
            expect(screen.getByText('Back')).toBeInTheDocument();
        });
    });

    it('completes tour on Finish click', async () => {
        const OnboardingTour = await getComponent();
        render(<OnboardingTour />);
        await waitFor(() => {
            expect(screen.getByText('Next')).toBeInTheDocument();
        });
        for (let i = 0; i < 4; i++) {
            fireEvent.click(screen.getByText('Next'));
            await vi.waitFor(() => {});
        }
        fireEvent.click(screen.getByText('Finish'));
        await waitFor(() => {
            expect(localStorage.getItem('onboarding_completed')).toBe('true');
        });
    });

    it('dismisses tour on X button click', async () => {
        const OnboardingTour = await getComponent();
        render(<OnboardingTour />);
        await waitFor(() => {
            expect(screen.getByText('X')).toBeInTheDocument();
        });
        fireEvent.click(screen.getByText('X'));
        await waitFor(() => {
            expect(localStorage.getItem('onboarding_completed')).toBe('true');
        });
    });

    it('dismisses tour on backdrop click', async () => {
        const OnboardingTour = await getComponent();
        const { container } = render(<OnboardingTour />);
        await waitFor(() => {
            expect(screen.getByText(/Welcome to ScholarForm/)).toBeInTheDocument();
        });
        const backdrop = container.querySelector('[class*="pointer-events-auto"]');
        if (backdrop) fireEvent.click(backdrop);
        await waitFor(() => {
            expect(localStorage.getItem('onboarding_completed')).toBe('true');
        });
    });

    it('shows step indicator dots', async () => {
        const OnboardingTour = await getComponent();
        const { container } = render(<OnboardingTour />);
        await waitFor(() => {
            const dots = container.querySelectorAll('.rounded-full');
            expect(dots.length).toBeGreaterThan(0);
        });
    });

    it('navigates back to previous step', async () => {
        const OnboardingTour = await getComponent();
        render(<OnboardingTour />);
        await waitFor(() => expect(screen.getByText('Next')).toBeInTheDocument());
        fireEvent.click(screen.getByText('Next'));
        await waitFor(() => expect(screen.getByText('Back')).toBeInTheDocument());
        fireEvent.click(screen.getByText('Back'));
        await waitFor(() => {
            expect(screen.getByText(/Welcome to ScholarForm/)).toBeInTheDocument();
        });
    });
});
