from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from app.models import Conversation, Order, ReturnRequest, Ticket, User, utcnow


def delivered_order(client):
    return next(order for order in client.get('/api/orders').json() if order['number'] == 'NS-1024')


def test_return_eligibility_tracks_remaining_quantities_and_rejections(client, login, db):
    login()
    order = delivered_order(client)
    user = db.scalar(select(User).where(User.email == 'customer@demo.local'))
    requests = []
    for item in order['items']:
        request = ReturnRequest(user_id=user.id, order_id=order['id'], item_id=item['id'],
                                quantity=item['quantity'], reason='Already requested', status='requested')
        db.add(request)
        requests.append(request)
    db.commit()
    exhausted = client.get(f"/api/orders/{order['id']}").json()
    assert exhausted['can_return'] is False
    assert all(item['returnable_quantity'] == 0 for item in exhausted['items'])
    requests[0].status = 'rejected'
    db.commit()
    restored = client.get(f"/api/orders/{order['id']}").json()
    assert restored['can_return'] is True
    assert next(item for item in restored['items'] if item['id'] == requests[0].item_id)['returnable_quantity'] == requests[0].quantity
    assert next(item for item in restored['items'] if item['id'] == requests[1].item_id)['returnable_quantity'] == 0


def test_future_delivery_does_not_advertise_return_eligibility(client, login, db):
    login()
    order = delivered_order(client)
    db.get(Order, order['id']).delivered_at = utcnow() + timedelta(days=1)
    db.commit()
    assert client.get(f"/api/orders/{order['id']}").json()['can_return'] is False


def test_team_removal_cannot_strand_an_assigned_ticket(client, login, db):
    customer_headers = login()
    conversation = client.post('/api/conversations', json={}, headers=customer_headers).json()
    ticket = client.post(f"/api/conversations/{conversation['id']}/handoff", headers=customer_headers).json()['ticket']
    staff_headers = login('support@demo.local')
    assert client.post(f"/api/staff/tickets/{ticket['id']}/claim", headers=staff_headers).status_code == 200
    staff = db.scalar(select(User).where(User.email == 'support@demo.local'))
    original_teams = list(staff.teams)
    admin_headers = login('admin@demo.local')
    response = client.patch(f'/api/admin/users/{staff.id}', json={'teams': ['billing']}, headers=admin_headers)
    assert response.status_code == 409
    assert 'assigned' in response.json()['detail'].lower()
    db.expire_all()
    assert db.get(User, staff.id).teams == original_teams
    staff_headers = login('support@demo.local')
    assert client.post(f"/api/staff/tickets/{ticket['id']}/resolve", headers=staff_headers,
                       json={'outcome': 'Customer question resolved', 'return_to_assistant': True}).status_code == 200
    admin_headers = login('admin@demo.local')
    assert client.patch(f'/api/admin/users/{staff.id}', json={'teams': ['billing']}, headers=admin_headers).status_code == 200


def test_whitespace_only_knowledge_cannot_be_published(client, login):
    headers = login('admin@demo.local')
    response = client.post('/api/admin/knowledge', headers=headers, json={
        'key': 'empty-policy', 'title': '   ', 'content': ' ' * 30, 'category': 'policy', 'approved': True,
    })
    assert response.status_code == 422
    assert not any(doc['key'] == 'empty-policy' for doc in client.get('/api/admin/knowledge').json())


def test_admin_intent_metrics_include_customer_turns_routed_directly_to_staff(client, login):
    headers = login()
    conversation = client.post('/api/conversations', json={}, headers=headers).json()
    message = client.post(f"/api/conversations/{conversation['id']}/messages", headers=headers, json={
        'content': 'Where is my refund?', 'client_message_id': str(uuid4()),
    })
    assert message.status_code == 200
    assert message.json()['ticket']['team'] == 'billing'
    login('admin@demo.local')
    assert client.get('/api/admin/metrics').json()['by_intent'].get('payment') == 1
