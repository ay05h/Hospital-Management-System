// app.js
function redirectTo(role) {
    const url = role === 'Admin' ? '/login' : `/register?role=${role}`;
    window.location.href = url;
}

function redirectToAdmin() {
    window.location.href = '/login?role=Admin';
}
const csrfToken = document.querySelector('input[name="csrf_token"]').value;

fetch('/book_appointment', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken  
    },
    body: JSON.stringify({
        doctor_id: doctorId,
        appointment_date: appointmentDate,
        start_time: startTime
    })
})
