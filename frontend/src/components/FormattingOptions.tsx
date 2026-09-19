import React from 'react';
import FormattingOptionsJsx from './upload/FormattingOptions';

export interface FormattingOptionsProps {
    [key: string]: any;
}

export function FormattingOptions(props: FormattingOptionsProps) {
    return <FormattingOptionsJsx {...props} />;
}
