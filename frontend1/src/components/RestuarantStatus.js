import React, { useEffect, useState } from 'react';
import io from 'socket.io-client';

const socket = io('http://localhost:3002');  // Replace with your backend server URL

const RestaurantStatus = () => {
  const [statusList, setStatusList] = useState([]);

  useEffect(() => {
    // Fetch initial status from the backend
    fetch('/get_status')
      .then((response) => response.json())
      .then((data) => {
        setStatusList(data);
      });

    // Listen for real-time status updates
    socket.on('status_update', (data) => {
      const { status, instances } = data;
      if (status === 'down') {
        setStatusList((prevStatusList) => prevStatusList.map((item) => {
          if (instances.includes(item.restaurant_id)) {
            return { ...item, restaurant_status: 0 };
          }
          return item;
        }));
      }
    });
  }, []);

  return (
    <div>
      <h2>Client Status</h2>
      <ul>
        {statusList.map((status) => (
          <li key={status.restaurant_id}>
            Client ID: {status.restaurant_id}, Status: {status.restaurant_status === 1 ? 'Online' : 'Down'}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default RestaurantStatus;
