import axios from 'axios';
import config from "@/config";

// Node 相关
export async function createNodeAPI(userId, nodeData) {
  const res = await axios.post(`${config.baseURL}/api/${userId}/nodes/add`, nodeData);
  return res.data; // 后端返回的 Node（含 id）
}

export async function updateNodeAPI(userId, nodeId, nodeData) {
  const res = await axios.put(`${config.baseURL}/api/${userId}/nodes/update/${nodeId}`, nodeData);
  return res.data;
}

export async function deleteNodeAPI(userId, nodeId) {
  await axios.delete(`${config.baseURL}/api/${userId}/nodes/delete/${nodeId}`);
}

// Link 相关
export async function createLinkAPI(userId, linkData) {
  const res = await axios.post(`${config.baseURL}/api/${userId}/links/add`, linkData);
  return res.data;
}

export async function updateLinkAPI(userId, linkId, linkData) {
  const res = await axios.put(`${config.baseURL}/api/${userId}/links/update/${linkId}`, linkData);
  return res.data;
}

export async function deleteLinkAPI(userId, linkId) {
  await axios.delete(`${config.baseURL}/api/${userId}/links/delete/${linkId}`);
}

// Instance 相关
export async function createInstanceAPI(userId, instanceData) {
  const res = await axios.post(`${config.baseURL}/api/${userId}/instance/add`, instanceData);
  return res.data;
}

export async function updateInstanceAPI(userId, instanceId, instanceData) {
  const res = await axios.put(`${config.baseURL}/api/${userId}/instance/update/${instanceId}`, instanceData);
  return res.data;
}

export async function deleteInstanceAPI(userId, instanceId) {
  await axios.delete(`${config.baseURL}/api/${userId}/instance/delete/${instanceId}`);
}