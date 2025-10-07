# Replacement Workflow Implementation

This document describes the implementation of the replacement workflow for the ESS system.

## Overview

The replacement workflow handles the process of finding and assigning replacement employees when a timeoff request is approved. The workflow includes:

1. **Timeoff Approval**: When a timeoff request is approved, the system automatically creates replacement requests
2. **Replacement Creation**: System finds available tasks and creates replacement records
3. **Employee Notification**: Available employees are notified about replacement opportunities
4. **Employee Acceptance**: Employees can accept replacement requests
5. **Admin Approval**: Administrators approve specific employees for replacements
6. **Webhook Notifications**: FastAPI backend is notified at each step

## Workflow Steps

### 1. Employee Requests Timeoff

- Employee submits timeoff request via mobile app
- API endpoint: `POST /api/app/timeoff`

### 2. Admin Approves Timeoff

- Admin approves the timeoff request in Odoo
- System automatically triggers replacement workflow
- Replacement records are created for available tasks

### 3. Replacement Creation

- System searches for tasks that need replacement during the leave period
- Creates replacement records with status "draft"
- Sends webhook notification: `replacement_created`

### 4. Employee Notification

- FastAPI backend receives webhook notification
- Notifies employees 2, 4, and 5 (who have `accept_replacements=True`)
- Mobile app displays replacement opportunities

### 5. Employee Acceptance

- Employees accept replacement requests via mobile app
- API endpoint: `POST /api/app/replacement_workflow/accept_replacement`
- System updates replacement record with accepted employees
- Sends webhook notification: `replacement_updated`

### 6. Admin Approval

- Admin selects final employee for replacement
- API endpoint: `POST /api/app/replacement_workflow/approve_replacement`
- System sets replacement status to "approved"
- Sends webhook notification: `replacement_approved`

## API Endpoints

### Replacement Workflow APIs

#### 1. Notify Available Replacements

```
POST /api/app/replacement_workflow/notify_available_replacements
```

Notifies employees that a replacement is available.

**Request Body:**

```json
{
  "replacement_id": 123
}
```

#### 2. Accept Replacement

```
POST /api/app/replacement_workflow/accept_replacement
```

Employee accepts a replacement request.

**Request Body:**

```json
{
  "replacement_id": 123,
  "employee_identification_id": "EMP001"
}
```

#### 3. Approve Replacement

```
POST /api/app/replacement_workflow/approve_replacement
```

Admin approves a specific employee for replacement.

**Request Body:**

```json
{
  "replacement_id": 123,
  "approved_employee_id": 456
}
```

#### 4. Get Available Replacements

```
GET /api/app/replacement_workflow/get_available_replacements
```

Gets list of employees who can accept replacements.

## Models

### 1. Webhook Notification (`isalis_ess.webhook_notification`)

Stores webhook notifications and their status.

**Fields:**

- `notification_type`: Type of notification
- `model_name`: Related model name
- `record_id`: Related record ID
- `webhook_url`: Webhook endpoint URL
- `status`: Notification status (pending, sent, failed, retry)
- `payload`: Notification payload data
- `retry_count`: Number of retry attempts

### 2. Webhook Configuration (`isalis_ess.webhook_config`)

Stores webhook URLs for different notification types.

**Fields:**

- `name`: Configuration name
- `notification_type`: Type of notification
- `webhook_url`: Webhook endpoint URL
- `is_active`: Whether configuration is active
- `company_id`: Company (for multi-company support)

### 3. Extended HR Leave (`hr.leave`)

Extended to handle replacement workflow.

**Methods:**

- `action_approve()`: Overridden to trigger replacement workflow
- `action_validate()`: Overridden to trigger replacement workflow
- `_handle_replacement_workflow()`: Handles replacement creation
- `_create_replacement_request()`: Creates replacement records

## Configuration

### Webhook URLs

Configure webhook URLs in Odoo:

1. Go to **Human Resources > Configuration > Webhook Configuration**
2. Create configurations for each notification type:
   - `replacement_created`: When replacement is created
   - `replacement_updated`: When employees accept replacement
   - `replacement_approved`: When admin approves replacement

### Employee Settings

Set `accept_replacements` field to `True` for employees who can accept replacements.

## Webhook Payloads

### Replacement Created

```json
{
  "event_type": "replacement_created",
  "replacement_id": 123,
  "task_id": 456,
  "task_name": "Task Name",
  "absent_employee_id": 789,
  "absent_employee_name": "Employee Name",
  "work_from_date": "2024-01-01",
  "work_to_date": "2024-01-05",
  "state": "draft",
  "timestamp": "2024-01-01T10:00:00"
}
```

### Replacement Updated

```json
{
  "event_type": "replacement_updated",
  "replacement_id": 123,
  "task_id": 456,
  "task_name": "Task Name",
  "absent_employee_id": 789,
  "absent_employee_name": "Employee Name",
  "employees_accept_replacements": [
    {
      "id": 101,
      "name": "Employee 2",
      "identification_id": "EMP002"
    },
    {
      "id": 103,
      "name": "Employee 4",
      "identification_id": "EMP004"
    }
  ],
  "state": "draft",
  "timestamp": "2024-01-01T10:00:00"
}
```

### Replacement Approved

```json
{
  "event_type": "replacement_approved",
  "replacement_id": 123,
  "task_id": 456,
  "task_name": "Task Name",
  "replacement_employee_id": 101,
  "replacement_employee_name": "Employee 2",
  "replacement_employee_identification_id": "EMP002",
  "absent_employee_id": 789,
  "absent_employee_name": "Employee Name",
  "work_from_date": "2024-01-01",
  "work_to_date": "2024-01-05",
  "state": "approved",
  "timestamp": "2024-01-01T10:00:00"
}
```

## Error Handling

### Webhook Failures

- System retries failed webhooks up to 3 times
- Failed webhooks are marked with error messages
- Manual retry option available in Odoo interface

### Validation

- Employee must have `accept_replacements=True` to accept replacements
- Replacement must be in "draft" state for acceptance
- Only employees who accepted can be approved

## Testing

### Test Scenarios

1. **Complete Workflow**: Test end-to-end replacement workflow
2. **Webhook Failures**: Test webhook retry mechanism
3. **Employee Validation**: Test employee eligibility checks
4. **State Transitions**: Test replacement state changes

### Test Data

- Create test employees with different `accept_replacements` values
- Create test timeoff requests
- Configure test webhook endpoints

## Troubleshooting

### Common Issues

1. **Webhook Not Sent**: Check webhook configuration and URLs
2. **Employee Not Notified**: Verify `accept_replacements` field value
3. **Replacement Not Created**: Check task availability and date ranges
4. **API Errors**: Review API logs and validation rules

### Logs

- Check Odoo logs for replacement workflow errors
- Monitor webhook notification status in Odoo interface
- Review API request/response logs

## Future Enhancements

1. **Automated Matching**: AI-based employee-replacement matching
2. **Skill-Based Assignment**: Consider employee skills for replacements
3. **Conflict Detection**: Prevent overlapping replacement assignments
4. **Performance Optimization**: Batch webhook notifications
5. **Mobile Push Notifications**: Direct push notifications to mobile apps
