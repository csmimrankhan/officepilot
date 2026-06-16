import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import FilePickerCard from './FilePickerCard.jsx'

describe('FilePickerCard', () => {
  const defaultProps = {
    message: 'Select your Excel file',
    onFileSelected: vi.fn(),
    onCancel: vi.fn(),
  }

  it('renders message and file picker UI', () => {
    render(<FilePickerCard {...defaultProps} />)
    expect(screen.getByText('Select your Excel file')).toBeTruthy()
    expect(screen.getByPlaceholderText('Select a file or enter path...')).toBeTruthy()
    expect(screen.getByText('Browse')).toBeTruthy()
    expect(screen.getByText('Continue')).toBeTruthy()
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  it('shows accepted file types', () => {
    render(<FilePickerCard {...defaultProps} acceptedTypes={['.xlsx', '.csv']} />)
    expect(screen.getByText(/\.xlsx/)).toBeTruthy()
    expect(screen.getByText(/\.csv/)).toBeTruthy()
  })

  it('shows error for unsupported extension entered via text', () => {
    render(<FilePickerCard {...defaultProps} />)
    const input = screen.getByPlaceholderText('Select a file or enter path...')
    fireEvent.change(input, { target: { value: 'test.pdf' } })
    expect(screen.getByText(/unsupported.*\.pdf/i)).toBeTruthy()
  })

  it('shows error for unsupported extension entered via text input then Continue', () => {
    const onSelected = vi.fn()
    render(<FilePickerCard {...defaultProps} onFileSelected={onSelected} />)
    const input = screen.getByPlaceholderText('Select a file or enter path...')
    fireEvent.change(input, { target: { value: 'test.pdf' } })
    fireEvent.click(screen.getByText('Continue'))
    expect(screen.getByText(/unsupported.*\.pdf/i)).toBeTruthy()
    expect(onSelected).not.toHaveBeenCalled()
  })

  it('calls onFileSelected with path when Continue clicked with valid xlsx', () => {
    const onSelected = vi.fn()
    render(<FilePickerCard {...defaultProps} onFileSelected={onSelected} />)
    const input = screen.getByPlaceholderText('Select a file or enter path...')
    fireEvent.change(input, { target: { value: 'C:\\data\\invoices.xlsx' } })
    fireEvent.click(screen.getByText('Continue'))
    expect(onSelected).toHaveBeenCalledWith('C:\\data\\invoices.xlsx')
  })

  it('calls onFileSelected with path when Continue clicked with valid csv', () => {
    const onSelected = vi.fn()
    render(<FilePickerCard {...defaultProps} onFileSelected={onSelected} />)
    const input = screen.getByPlaceholderText('Select a file or enter path...')
    fireEvent.change(input, { target: { value: '/home/user/sales.csv' } })
    fireEvent.click(screen.getByText('Continue'))
    expect(onSelected).toHaveBeenCalledWith('/home/user/sales.csv')
  })

  it('calls onCancel when Cancel clicked', () => {
    const onCancel = vi.fn()
    render(<FilePickerCard {...defaultProps} onCancel={onCancel} />)
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalled()
  })

  it('renders without onCancel', () => {
    render(<FilePickerCard message="Pick a file" onFileSelected={vi.fn()} />)
    expect(screen.queryByText('Cancel')).toBeNull()
  })

  it('Continue button is disabled when path is empty', () => {
    render(<FilePickerCard {...defaultProps} />)
    const btn = screen.getByText('Continue')
    expect(btn.disabled).toBe(true)
  })

  it('clears error when valid file is entered after error', () => {
    render(<FilePickerCard {...defaultProps} />)
    const input = screen.getByPlaceholderText('Select a file or enter path...')
    fireEvent.change(input, { target: { value: 'test.pdf' } })
    expect(screen.getByText(/unsupported/i)).toBeTruthy()
    fireEvent.change(input, { target: { value: 'test.xlsx' } })
    expect(screen.queryByText(/unsupported/i)).toBeNull()
  })

  it('accepts custom acceptedTypes prop', () => {
    render(<FilePickerCard {...defaultProps} acceptedTypes={['.xlsm']} />)
    expect(screen.getByText(/\.xlsm/)).toBeTruthy()
  })
})
