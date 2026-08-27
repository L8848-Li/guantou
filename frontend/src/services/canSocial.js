import request from '@/utils/request';

export function likeCan(canId) {
  return request.put(`/cans/${canId}/like/`);
}

export function unlikeCan(canId) {
  return request.del(`/cans/${canId}/like/`);
}

export function listCanComments(canId, params = {}) {
  return request.get('/comments/', { can_id: canId, ...params });
}

export function createCanComment(canId, content, parentId = null) {
  const payload = { can_id: canId, content };
  if (parentId) payload.parent_id = parentId;
  return request.post('/comments/', payload);
}

export function listNameplateComments(nameplateId, params = {}) {
  return request.get('/comments/', { nameplate_id: nameplateId, ...params });
}

export function createNameplateComment(nameplateId, content, parentId = null) {
  const payload = { nameplate_id: nameplateId, content };
  if (parentId) payload.parent_id = parentId;
  return request.post('/comments/', payload);
}

export function deleteCanComment(commentId) {
  return request.del(`/comments/${commentId}/`);
}

export function likeCanComment(commentId) {
  return request.put(`/comments/${commentId}/like/`);
}

export function unlikeCanComment(commentId) {
  return request.del(`/comments/${commentId}/like/`);
}

export function listCanPosts(canId, params = {}) {
  return request.get('/posts/', { can_id: canId, ...params });
}

export function getCanPost(postId) {
  return request.get(`/posts/${postId}/`);
}

export function createCanPost(canId, text = '', visibility = 'public') {
  return request.post('/posts/', {
    can_id: Number(canId),
    text: String(text || '').trim(),
    visibility,
  });
}

export function deleteCanPost(postId) {
  return request.del(`/posts/${postId}/`);
}

export default {
  createCanComment,
  createNameplateComment,
  createCanPost,
  deleteCanComment,
  deleteCanPost,
  getCanPost,
  likeCan,
  likeCanComment,
  listCanComments,
  listNameplateComments,
  listCanPosts,
  unlikeCan,
  unlikeCanComment,
};
