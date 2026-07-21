import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import Skeleton from '../components/ui/Skeleton';
import Card from '../components/ui/Card';
import StatusBadge from '../components/StatusBadge';

describe('Button visual snapshots', () => {
    it('primary variant', () => {
        const { container } = render(<Button variant="primary">Primary</Button>);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('secondary variant', () => {
        const { container } = render(<Button variant="secondary">Secondary</Button>);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('danger variant', () => {
        const { container } = render(<Button variant="danger">Danger</Button>);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('loading state', () => {
        const { container } = render(<Button loading>Loading</Button>);
        expect(container.innerHTML).toMatchSnapshot();
    });
});

describe('Input visual snapshots', () => {
    it('normal state', () => {
        const { container } = render(<Input placeholder="Enter text..." />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('with error', () => {
        const { container } = render(<Input placeholder="Email" error="Invalid email address" />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('with helper text', () => {
        const { container } = render(<Input placeholder="Password" helperText="Must be at least 8 characters" />);
        expect(container.innerHTML).toMatchSnapshot();
    });
});

describe('Badge visual snapshots', () => {
    it('completed status', () => {
        const { container } = render(<Badge status="completed">Completed</Badge>);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('failed status', () => {
        const { container } = render(<Badge status="failed">Failed</Badge>);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('processing status', () => {
        const { container } = render(<Badge status="processing">Processing</Badge>);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('pending status', () => {
        const { container } = render(<Badge status="pending">Pending</Badge>);
        expect(container.innerHTML).toMatchSnapshot();
    });
});

describe('EmptyState visual snapshots', () => {
    it('without action', () => {
        const { container } = render(<EmptyState title="Nothing here" description="No items found." />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('with action', () => {
        const { container } = render(
            <EmptyState title="No documents" description="Upload your first document." actionLabel="Upload" onAction={() => {}} />
        );
        expect(container.innerHTML).toMatchSnapshot();
    });
});

describe('Skeleton visual snapshots', () => {
    it('small size', () => {
        const { container } = render(<Skeleton width={48} height={48} />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('medium size', () => {
        const { container } = render(<Skeleton width={200} height={16} />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('large size', () => {
        const { container } = render(<Skeleton width={400} height={200} />);
        expect(container.innerHTML).toMatchSnapshot();
    });
});

describe('Card visual snapshots', () => {
    it('normal variant', () => {
        const { container } = render(<Card>Normal card content</Card>);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('glass variant', () => {
        const { container } = render(<Card glass>Glass card content</Card>);
        expect(container.innerHTML).toMatchSnapshot();
    });
});

describe('StatusBadge visual snapshots', () => {
    it('PROCESSING status', () => {
        const { container } = render(<StatusBadge status="PROCESSING" />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('COMPLETED status', () => {
        const { container } = render(<StatusBadge status="COMPLETED" />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('COMPLETED_WITH_WARNINGS status', () => {
        const { container } = render(<StatusBadge status="COMPLETED_WITH_WARNINGS" />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('FAILED status', () => {
        const { container } = render(<StatusBadge status="FAILED" />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('CANCELLED status', () => {
        const { container } = render(<StatusBadge status="CANCELLED" />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('PENDING status', () => {
        const { container } = render(<StatusBadge status="PENDING" />);
        expect(container.innerHTML).toMatchSnapshot();
    });

    it('STANDBY status', () => {
        const { container } = render(<StatusBadge status="STANDBY" />);
        expect(container.innerHTML).toMatchSnapshot();
    });
});
